
def test_event_logger_service(event_logger, mongo_storage, log_record):
    mongo_storage.clear()
    event_logger.mongo_storage = mongo_storage
    event_logger.emit(log_record)

    assert mongo_storage.count() == 1
    assert mongo_storage.collection.find_one() == log_record.__dict__
    mongo_storage.clear()