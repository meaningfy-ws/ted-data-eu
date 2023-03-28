import tempfile
from pathlib import Path
from threading import Lock
from typing import List, Optional
import semantic_version
from pymongo import MongoClient
from ted_sws.core.model.manifestation import RDFManifestation
from ted_sws.core.model.notice import Notice, NoticeStatus
from ted_sws.core.model.transform import MappingSuite
from ted_sws.data_manager.adapters.mapping_suite_repository import MappingSuiteRepositoryMongoDB, \
    MappingSuiteRepositoryInFileSystem
from ted_sws.data_manager.adapters.notice_repository import NoticeRepository
from ted_sws.event_manager.services.log import log_notice_error
from ted_sws.notice_metadata_processor.services.notice_eligibility import check_package
from ted_sws.notice_transformer.adapters.rml_mapper import RMLMapper
from collections import defaultdict
import shutil

from ted_data_eu import config

DATA_SOURCE_PACKAGE = "data"
DEFAULT_TRANSFORMATION_FILE_EXTENSION = ".ttl"

import uuid


def make_temp_path(tmp_dir=tempfile.gettempdir()):
    return Path(tmp_dir) / str(uuid.uuid1())


def notice_eligibility_checker(notice: Notice, mapping_suites: List[MappingSuite]) -> Optional[str]:
    """
    Check if notice in eligible for transformation
    :param mapping_suites:
    :param notice:
    :return:
    """

    possible_mapping_suites = []
    for mapping_suite in mapping_suites:
        if check_package(mapping_suite=mapping_suite, notice_metadata=notice.normalised_metadata):
            possible_mapping_suites.append(mapping_suite)

    if possible_mapping_suites:
        best_version = semantic_version.Version(possible_mapping_suites[0].version)
        mapping_suite_identifier_with_version = possible_mapping_suites[0].identifier
        for mapping_suite in possible_mapping_suites[1:]:
            if semantic_version.Version(mapping_suite.version) > best_version:
                best_version = semantic_version.Version(mapping_suite.version)
                mapping_suite_identifier_with_version = mapping_suite.identifier

        notice.set_is_eligible_for_transformation(eligibility=True)
        return mapping_suite_identifier_with_version
    else:
        notice.set_is_eligible_for_transformation(eligibility=False)

    return None


class MappingSuiteTransformationPool:

    def __init__(self, mongodb_client: MongoClient, transformation_timeout: float = None):
        mapping_suite_repository = MappingSuiteRepositoryMongoDB(mongodb_client=mongodb_client)
        self.notice_repository = NoticeRepository(mongodb_client=mongodb_client)
        self.mapping_suites = []
        for mapping_suite in mapping_suite_repository.list():
            mapping_suite.transformation_test_data.test_data = []
            new_identifier = mapping_suite.get_mongodb_id()
            mapping_suite.identifier = new_identifier
            self.mapping_suites.append(mapping_suite)
        self.rml_mapper = RMLMapper(rml_mapper_path=config.RML_MAPPER_PATH,
                                    transformation_timeout=transformation_timeout)
        self.mappings_pool_tmp_dirs = defaultdict(list)
        self.mappings_pool_dirs = {}
        self.mappings_pool_dir = make_temp_path()
        self.mappings_pool_dir.mkdir(parents=True, exist_ok=True)
        self.sync_mutex = Lock()
        for mapping_suite in self.mapping_suites:
            package_path = self.mappings_pool_dir / mapping_suite.identifier
            mapping_suite_repository = MappingSuiteRepositoryInFileSystem(repository_path=self.mappings_pool_dir)
            mapping_suite_repository.add(mapping_suite=mapping_suite)
            data_source_path = package_path / DATA_SOURCE_PACKAGE
            data_source_path.mkdir(parents=True, exist_ok=True)
            self.mappings_pool_dirs[mapping_suite.identifier] = package_path

    def reserve_mapping_suite_path_by_id(self, mapping_suite_id: str) -> Path:
        self.sync_mutex.acquire()
        mapping_suite_cached_path = self.mappings_pool_tmp_dirs[mapping_suite_id].pop() if self.mappings_pool_tmp_dirs[
            mapping_suite_id] else None
        self.sync_mutex.release()
        if not mapping_suite_cached_path:
            mapping_suite_path = self.mappings_pool_dirs[mapping_suite_id]
            tmp_dir = make_temp_path()
            shutil.copytree(mapping_suite_path, tmp_dir)
            return tmp_dir
        return mapping_suite_cached_path

    def release_mapping_suite_path_by_id(self, mapping_suite_id: str, mapping_suite_path: Path):
        self.sync_mutex.acquire()
        self.mappings_pool_tmp_dirs[mapping_suite_id].append(mapping_suite_path)
        self.sync_mutex.release()

    def transform_notice_by_id(self, notice_id: str) -> Optional[str]:
        notice = self.notice_repository.get(notice_id)
        mapping_suite_id = notice_eligibility_checker(notice, self.mapping_suites)
        if mapping_suite_id:
            notice.update_status_to(new_status=NoticeStatus.PREPROCESSED_FOR_TRANSFORMATION)
            working_package_path = self.reserve_mapping_suite_path_by_id(mapping_suite_id)
            try:
                data_source_path = working_package_path / DATA_SOURCE_PACKAGE
                data_source_path.mkdir(parents=True, exist_ok=True)
                notice_path = data_source_path / "source.xml"
                notice_path.write_text(data=notice.xml_manifestation.object_data, encoding="utf-8")
                rdf_result = self.rml_mapper.execute(package_path=working_package_path)
                notice.set_rdf_manifestation(
                    rdf_manifestation=RDFManifestation(mapping_suite_id=mapping_suite_id,
                                                       object_data=rdf_result))
                self.notice_repository.update(notice)
                self.release_mapping_suite_path_by_id(mapping_suite_id, working_package_path)
                return notice_id
            except Exception as e:
                self.release_mapping_suite_path_by_id(mapping_suite_id, working_package_path)
                notice_normalised_metadata = notice.normalised_metadata
                log_notice_error(message=str(e), notice_id=notice_id, domain_action="rml_pool_transformation",
                                 notice_form_number=notice_normalised_metadata.form_number if notice_normalised_metadata else None,
                                 notice_status=notice.status if notice else None,
                                 notice_eforms_subtype=notice_normalised_metadata.eforms_subtype if notice_normalised_metadata else None)
                return None

    def close(self):
        shutil.rmtree(self.mappings_pool_dir)
        for mapping_suite_id, mappings_pool_tmp_dirs in self.mappings_pool_tmp_dirs.items():
            for mappings_pool_tmp_dir in mappings_pool_tmp_dirs:
                shutil.rmtree(mappings_pool_tmp_dir)


def transform_notice_by_id(notice_id: str, mapping_transformation_pool: MappingSuiteTransformationPool) -> str:
    return mapping_transformation_pool.transform_notice_by_id(notice_id=notice_id)
