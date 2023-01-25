import pytest

from ted_data_eu.adapters.triple_store import GraphDBAdapter
from tests.test_data import TEST_RDF_MANIFESTATIONS_PATH

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
