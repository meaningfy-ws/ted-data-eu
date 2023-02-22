import abc
from typing import Dict, List


class StorageABC(abc.ABC):
    """
       This class implements a common interface for all storages.
    """


class DocumentStorageABC(StorageABC):
    """
       This class is intended for storing Document objects.
    """

    @abc.abstractmethod
    def add_document(self, document: Dict):
        """
            This method allows you to add document object to the storage.
        :param document:
        :return:
        """

    @abc.abstractmethod
    def add_documents(self, documents: List[Dict]):
        """
            This method allows you to add documents objects to the storage.
        :param documents:
        :return:
        """

    @abc.abstractmethod
    def query(self, query: Dict):
        """
            This method allows you to query data in storage.
        :param query:
        :return:
        """

    @abc.abstractmethod
    def clear(self):
        """
            This method clears storage.
        :return:
        """