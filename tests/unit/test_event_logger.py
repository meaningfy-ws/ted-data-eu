from ted_data_eu.adapters.event_logger import MongoDBEventLogger


def test_event_logger(event_logger: MongoDBEventLogger):
    assert event_logger is not None
    assert event_logger.mongo_storage is not None
