import json
from typing import Dict, List

import requests
from requests.auth import HTTPBasicAuth

from ted_data_eu import config
from ted_data_eu.adapters.storage_abc import DocumentStorageABC

BASIC_HEADERS = {'Content-type': 'application/x-ndjson'}


class ElasticStorageException(Exception):
    """
        Implements custom exception for ElasticStorage
    """
    pass


class ElasticStorage(DocumentStorageABC):
    """
       Implements interaction with ElasticSearch storage by using its API.
    """

    def __init__(self,
                 elastic_index: str,
                 host: str = None,
                 user: str = None,
                 password: str = None):
        """
           Implements interaction with ElasticSearch storage by using its API.

            :param elastic_index: ElasticSearch index (schema) where the documents will be stored
            :param host: Elastic API host and port (if different from the defaults for http and https)
            :param user: Elastic API user
            :param password: Elastic API password
            :return:
        """
        self.host = host or config.ELASTIC_HOST
        self.auth = HTTPBasicAuth(user or config.ELASTIC_USER,
                                  password or config.ELASTIC_PASSWORD)
        self.elastic_index = elastic_index

    def add_document(self, document: Dict):
        """
           Add document to storage.

            :param document: Document to be stored
            :return:
        """
        response = requests.post(url=f"{self.host}/{self.elastic_index}/_doc/",
                                 headers=BASIC_HEADERS,
                                 auth=self.auth,
                                 data=json.dumps(document))
        deserialized_response = json.loads(response.content)
        if response.status_code != 201:
            raise ElasticStorageException(
                f"Elastic API add_document() error: {deserialized_response['error']['caused_by']['reason']}")

    def add_documents(self, documents: List[Dict]):
        """
           Add documents to storage using Elastic API bulk.

            :param documents: List of documents to be stored
            :return:
        """
        data_to_send = []
        for document in documents:
            data_to_send.append(json.dumps({"create": {"_index": self.elastic_index}}))
            data_to_send.append(json.dumps(document))
        response = requests.post(url=f"{self.host}/{self.elastic_index}/_bulk",
                                 headers=BASIC_HEADERS,
                                 auth=self.auth,
                                 data='\n'.join(line for line in data_to_send) + '\n')
        deserialized_response = json.loads(response.content)
        if response.status_code != 200:
            raise ElasticStorageException(
                f"Elastic API add_documents() error: {deserialized_response['error']['caused_by']['reason']}")

    def clear(self):
        """
            Delete current index.

        :return:
        """
        response = requests.delete(url=f"{self.host}/{self.elastic_index}",
                                   headers=BASIC_HEADERS,
                                   auth=self.auth)
        deserialized_response = json.loads(response.content)
        if response.status_code != 200:
            raise ElasticStorageException(
                f"Elastic API clear() error: {deserialized_response['error']['caused_by']['reason']}")

    def count(self) -> int:
        """
            Return number of documents from current ElasticSearch Index.

        :return:
        """
        response = requests.post(url=f"{self.host}/{self.elastic_index}/_count",
                                 headers=BASIC_HEADERS,
                                 auth=self.auth)
        deserialized_response = json.loads(response.content)
        if response.status_code != 200:
            raise ElasticStorageException(
                f"Elastic API count() error: {deserialized_response['error']['caused_by']['reason']}")
        return deserialized_response['count']
