import pytest

from ted_data_eu.adapters.storage import ElasticStorage
from ted_data_eu.adapters.triple_store import GraphDBAdapter
from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import TedDataETLPipeline
from tests.test_data import TEST_RDF_MANIFESTATIONS_PATH, TEST_DOCUMENTS_PATH, TEST_NOTICES_PATH

REPOSITORY_NAME = "unknown_repository_123456677"
SPARQL_QUERY_TRIPLES = "select * {?s ?p ?o}"


@pytest.fixture
def rdf_file_path():
    return TEST_RDF_MANIFESTATIONS_PATH / 'example.ttl'


@pytest.fixture
def tmp_repository_name():
    return REPOSITORY_NAME


@pytest.fixture
def sparql_query_triples():
    return SPARQL_QUERY_TRIPLES


@pytest.fixture
def graphdb_triple_store():
    return GraphDBAdapter()


@pytest.fixture
def test_repository_names():
    return ['tmp_test_repo1', 'tmp_test_repo2']


@pytest.fixture
def document_file_path():
    return TEST_DOCUMENTS_PATH / 'example.json'


@pytest.fixture
def elastic_index():
    return 'test_ted_data'


@pytest.fixture
def elastic_storage(elastic_index):
    return ElasticStorage(elastic_index=elastic_index)


@pytest.fixture
def elastic_query():
    return {"match_all": {}}


@pytest.fixture
def ted_data_etl_pipeline():
    return TedDataETLPipeline()


@pytest.fixture
def etl_pipeline_config():
    return {"start_date": "20180314", "end_date": "20180314"}


@pytest.fixture
def example_notices():
    return list(TEST_NOTICES_PATH.iterdir())
