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
from ted_sws.notice_metadata_processor.services.notice_eligibility import check_package
from ted_sws.notice_transformer.adapters.rml_mapper import RMLMapper
from collections import defaultdict
import shutil

from ted_data_eu import config

DATA_SOURCE_PACKAGE = "data"
DEFAULT_TRANSFORMATION_FILE_EXTENSION = ".ttl"


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
        mapping_suite_identifier_with_version = possible_mapping_suites[0].get_mongodb_id()
        for mapping_suite in possible_mapping_suites[1:]:
            if semantic_version.Version(mapping_suite.version) > best_version:
                best_version = semantic_version.Version(mapping_suite.version)
                mapping_suite_identifier_with_version = mapping_suite.get_mongodb_id()

        notice.set_is_eligible_for_transformation(eligibility=True)
        return mapping_suite_identifier_with_version
    else:
        notice.set_is_eligible_for_transformation(eligibility=False)

    return None


class MappingSuiteTransformationPool:

    def __init__(self, mongodb_client: MongoClient):
        mapping_suite_repository = MappingSuiteRepositoryMongoDB(mongodb_client=mongodb_client)
        self.notice_repository = NoticeRepository(mongodb_client=mongodb_client)
        self.mapping_suites = []
        for mapping_suite in mapping_suite_repository.list():
            mapping_suite.transformation_test_data.test_data = []
            self.mapping_suites.append(mapping_suite)
        self.rml_mapper = RMLMapper(rml_mapper_path=config.RML_MAPPER_PATH)
        self.mappings_pool_tmp_dirs = defaultdict(list)
        self.mappings_pool_dirs = {}
        self.mappings_pool_dir = tempfile.TemporaryDirectory()
        self.sync_mutex = Lock()
        for mapping_suite in self.mapping_suites:
            package_path = Path(self.mappings_pool_dir.name) / mapping_suite.get_mongodb_id()
            mapping_suite_repository = MappingSuiteRepositoryInFileSystem(repository_path=package_path.parent)
            mapping_suite_repository.add(mapping_suite=mapping_suite)
            data_source_path = package_path / DATA_SOURCE_PACKAGE
            data_source_path.mkdir(parents=True, exist_ok=True)
            self.mappings_pool_dirs[mapping_suite.get_mongodb_id()] = package_path

    def reserve_mapping_suite_path_by_id(self, mapping_suite_id: str) -> Path:
        self.sync_mutex.acquire()
        mapping_suite_cached_path = self.mappings_pool_tmp_dirs[mapping_suite_id].pop()
        self.sync_mutex.release()
        if not mapping_suite_cached_path:
            mapping_suite_path = self.mappings_pool_dirs[mapping_suite_id]
            tmp_dir = tempfile.TemporaryDirectory()
            shutil.copytree(mapping_suite_path, Path(tmp_dir.name))
            return Path(tmp_dir.name)
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
            data_source_path = working_package_path / DATA_SOURCE_PACKAGE
            notice_path = data_source_path / "source.xml"
            notice_path.write_text(data=notice.xml_manifestation.object_data, encoding="utf-8")
            rdf_result = self.rml_mapper.execute(package_path=working_package_path)
            self.release_mapping_suite_path_by_id(mapping_suite_id, working_package_path)
            notice.set_rdf_manifestation(
                rdf_manifestation=RDFManifestation(mapping_suite_id=mapping_suite_id,
                                                   object_data=rdf_result))
        self.notice_repository.update(notice)

        if mapping_suite_id:
            return notice_id
        else:
            return None

    def close(self):
        self.mappings_pool_dir.cleanup()
        for mapping_suite_id, mappings_pool_tmp_dirs in self.mappings_pool_tmp_dirs.items():
            for mappings_pool_tmp_dir in mappings_pool_tmp_dirs:
                shutil.rmtree(mappings_pool_tmp_dir)


def transform_notice_by_id(notice_id: str, mapping_transformation_pool: MappingSuiteTransformationPool) -> str:
    return mapping_transformation_pool.transform_notice_by_id(notice_id=notice_id)
