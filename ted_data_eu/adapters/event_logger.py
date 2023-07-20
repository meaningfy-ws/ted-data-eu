import logging

from ted_data_eu import config
from ted_data_eu.adapters.storage import MongoDBStorage


class MongoDBEventLogger(logging.StreamHandler):
    """
        Implements logging handler for MongoDB storage.
    """

    def __init__(self,
                 database_name: str,
                 collection_name: str,
                 mongo_auth_url: str = None,
                 ):
        """
            Implements logging handler for MongoDB storage.

            :param database_name: MongoDB database name where the documents will be stored
            :param collection_name: MongoDB collection name where the documents will be stored
            :param mongo_auth_url: MongoDB authentication URL
            :return:
        """
        super().__init__()
        self.database_name = database_name
        self.collection_name = collection_name
        self.mongo_auth_url = mongo_auth_url or config.MONGO_DB_AUTH_URL
        self.mongo_storage = MongoDBStorage(database_name=self.database_name,
                                            collection_name=self.collection_name,
                                            mongo_auth_url=self.mongo_auth_url)

    def emit(self, record: logging.LogRecord):
        """
            Add document to storage.

            :param record: Log record to be stored
            :return:
        """
        self.mongo_storage.add_document(record.__dict__)
