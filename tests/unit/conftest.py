import pytest

from ted_data_eu.adapters.cpv_processor import CPVProcessor
from ted_data_eu.adapters.nuts_processor import NUTSProcessor


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