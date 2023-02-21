import json
from typing import Dict, List

import requests
from requests import Response
from requests.auth import HTTPBasicAuth

from ted_data_eu import config
from ted_data_eu.adapters.storage_abc import DocumentStorageABC

BASIC_HEADERS = {'Content-type': 'application/x-ndjson'}


class ElasticStorage(DocumentStorageABC):
    """
       Implements interaction with ElasticSearch storage by using its API.
    """

    def __init__(self,
                 index: str,
                 host: str = None,
                 user: str = None,
                 password: str = None):
        """
           Implements interaction with ElasticSearch storage by using its API.

            :param index: ElasticSearch index (schema) where the documents will be stored
            :param host: Elastic API host and port (if different from the defaults for http and https)
            :param user: Elastic API user
            :param password: Elastic API password
            :return:
        """
        self.host = host or config.ELASTIC_HOST
        self.auth = HTTPBasicAuth(user or config.ELASTIC_USER,
                                  password or config.ELASTIC_PASSWORD)
        self.index = index

    def add_document(self, document: str) -> Response:
        """
           Add document to storage.

            :param document: Document to be stored
            :return:
        """
        response = requests.post(url=f"{self.host}/{self.index}/_doc/",
                                 headers=BASIC_HEADERS,
                                 auth=self.auth,
                                 data=document)
        return response

    def add_documents(self, documents: List[str]) -> Response:
        """
           Add documents to storage using Elastic API bulk.

            :param documents: List of documents to be stored
            :return:
        """
        data_to_send = []
        for document in documents:
            data_to_send.append(json.dumps({"create": {"_index": self.index}}))
            data_to_send.append(document)
        response = requests.post(url=f"{self.host}/{self.index}/_bulk",
                                 headers=BASIC_HEADERS,
                                 auth=self.auth,
                                 data='\n'.join(line for line in data_to_send) + '\n')
        return response

    def query(self, query: str) -> Response:
        """
            Query storage using Elastic API query parameters.

        :param query: Elastic API query
        :return:
        """
        response = requests.get(url=f"{self.host}/{self.index}/_search",
                                headers=BASIC_HEADERS,
                                auth=self.auth,
                                data=query)
        return response

    def clear(self):
        """
            Delete current index.

        :return:
        """
        response = requests.delete(url=f"{self.host}/{self.index}",
                                   headers=BASIC_HEADERS,
                                   auth=self.auth)
        return response
