from ted_data_eu.services.dummy_service import dummy_service_does_dummy_stuff


def test_dummy_e2e():
    assert dummy_service_does_dummy_stuff()