from pymongo import MongoClient
# from ted_sws import config
from ted_sws.data_manager.adapters.notice_repository import NoticeRepository
from ted_sws.notice_fetcher.services.notice_fetcher import NoticeFetcher
from ted_sws.notice_fetcher.adapters.ted_api import TedAPIAdapter, TedRequestAPI
from ted_sws.notice_metadata_processor.services.metadata_normalizer import normalise_notice
from ted_sws.data_sampler.services.notice_xml_indexer import index_notice
from ted_sws.data_manager.adapters.mapping_suite_repository import MappingSuiteRepositoryMongoDB
from ted_sws.notice_metadata_processor.services.notice_eligibility import notice_eligibility_checker
from ted_sws.core.model.notice import NoticeStatus, Notice
from ted_sws.notice_transformer.adapters.rml_mapper import RMLMapper
from ted_sws.notice_transformer.services.notice_transformer import transform_notice

EXAMPLE_NOTICE_ID = '508252-2022'
EXAMPLE_WILDCARD_DATE = "20220203*"
MONGO_DB_AUTH_URL = 'mongodb://root:example@localhost:27017/'
MAPPING_SUITE_PACKAGE_NAME = 'package_F03_test'


def _get_ted_api_adapter():
    ted_api_adapter = TedAPIAdapter(request_api=TedRequestAPI(), ted_api_url='https://ted.europa.eu/api/v2.0/notices/search')
    assert ted_api_adapter
    return ted_api_adapter


def test_get_notice_by_id():
    ted_api_adapter = _get_ted_api_adapter()
    example_notice_dict = ted_api_adapter.get_by_id(document_id=EXAMPLE_NOTICE_ID)
    assert example_notice_dict


def test_fetch_notice():
    ted_api_adapter = _get_ted_api_adapter()
    assert ted_api_adapter
    mongo_client = MongoClient(MONGO_DB_AUTH_URL)
    assert mongo_client
    notice_repository = NoticeRepository(mongodb_client=mongo_client)
    assert notice_repository
    notice_fetcher = NoticeFetcher(notice_repository=notice_repository, ted_api_adapter=ted_api_adapter)
    assert notice_fetcher
    notice_fetcher.fetch_notice_by_id(document_id=EXAMPLE_NOTICE_ID)
    notice_from_mongo = notice_repository.get(EXAMPLE_NOTICE_ID)
    assert notice_from_mongo


def test_normalise_notice():
    mongo_client = MongoClient(MONGO_DB_AUTH_URL)
    assert mongo_client
    notice_repository = NoticeRepository(mongodb_client=mongo_client)
    assert notice_repository
    notice = notice_repository.get(reference=EXAMPLE_NOTICE_ID)
    assert notice
    # TODO: de scos indexarea
    notice = index_notice(notice=notice)
    assert notice
    try:
        normalised_notice = normalise_notice(notice)
    except Exception as e:
        raise e
    assert normalised_notice
    notice_repository.update(normalised_notice)


def test_transform_notice():
    mongodb_client = MongoClient(MONGO_DB_AUTH_URL)
    notice_repository = NoticeRepository(mongodb_client=mongodb_client)
    notice = notice_repository.get(EXAMPLE_NOTICE_ID)

    mapping_suite_repository = MappingSuiteRepositoryMongoDB(mongodb_client=mongodb_client)
    # TODO: de vazult daca trebuie sa fie ceva in mappingsuite repo
    result = notice_eligibility_checker(notice=notice, mapping_suite_repository=mapping_suite_repository)

    assert result

    # mapping_suite = mapping_suite_repository.get(reference=mapping_suite_id)

    # rml_mapper = RMLMapper(rml_mapper_path=config.RML_MAPPER_PATH)
    # transform_notice()


def test_get_notices_by_wildcard():
    ted_api_adapter = _get_ted_api_adapter()
    example_notices_list = ted_api_adapter.get_by_wildcard_date(wildcard_date=EXAMPLE_WILDCARD_DATE)
    assert example_notices_list


if __name__ == '__main__':
    test_fetch_notice()
    test_normalise_notice()
    test_transform_notice()
