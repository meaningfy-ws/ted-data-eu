import pytest

from ted_data_eu import config
from ted_data_eu.adapters.cpv_processor import CPVProcessor, CellarCPVProcessor
from ted_data_eu.adapters.nuts_processor import NUTSProcessor, CellarNUTSProcessor
from ted_data_eu.adapters.triple_store import TDATripleStoreEndpoint
from ted_data_eu.services.etl_pipelines.postgres_etl_pipeline import CELLAR_ENDPOINT_URL


@pytest.fixture
def cpv_processor():
    return CPVProcessor()


@pytest.fixture
def fake_cpv():
    return '12345678'


@pytest.fixture
def real_cpv():
    return '63712321'


@pytest.fixture
def problematic_cpv():
    return '60112000'


@pytest.fixture
def real_nuts():
    return 'FRK26'


@pytest.fixture
def fake_nuts():
    return None


@pytest.fixture
def nuts_processor():
    return NUTSProcessor()

@pytest.fixture
def cellar_nuts_processor():
    return CellarNUTSProcessor(TDATripleStoreEndpoint(CELLAR_ENDPOINT_URL).with_query(config.CELLAR_TABLE_QUERY_PATHS['NUTS'].read_text(encoding='utf-8')).fetch_csv())

@pytest.fixture
def cellar_cpv_processor():
    return CellarCPVProcessor(TDATripleStoreEndpoint(CELLAR_ENDPOINT_URL).with_query(config.CELLAR_TABLE_QUERY_PATHS['Purpose'].read_text(encoding='utf-8')).fetch_csv())