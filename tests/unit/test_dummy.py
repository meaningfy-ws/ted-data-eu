from ted_data_eu.services.dummy_service import dummy_service_does_dummy_stuff
from string import Template
from ted_data_eu import config
def test_dummy_unit():
    assert dummy_service_does_dummy_stuff()