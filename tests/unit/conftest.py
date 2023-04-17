import pytest

from ted_data_eu.adapters.cpv import CPVAlgorithms


@pytest.fixture
def cpv_algorithms_object():
    return CPVAlgorithms()


@pytest.fixture
def fake_cpv():
    return '12345678'


@pytest.fixture
def real_cpv():
    return '63712321'


@pytest.fixture
def problematic_cpv():
    return '60112000'
