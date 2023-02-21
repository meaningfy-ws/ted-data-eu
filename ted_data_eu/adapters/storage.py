import json
from typing import Dict, List

import requests
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
                 host: str = config.ELASTIC_HOST,
                 user: str = config.ELASTIC_USER,
                 password: str = config.ELASTIC_PASSWORD):
        """
           Implements interaction with ElasticSearch storage by using its API.

            :param index: ElasticSearch index (schema) where the documents will be stored
            :param host: Elastic API host and port (if different from the defaults for http and https)
            :param user: Elastic API user
            :param password: Elastic API password
            :return:
        """
        self.host = host
        self.auth = HTTPBasicAuth(user, password)
        self.index = index

    def add_document(self, document: Dict) -> Dict:
        """
           Add document to storage.

            :param document: Document to be stored
            :return:
        """
        response = requests.post(url=f"{self.host}/{self.index}/_doc/",
                                 headers=BASIC_HEADERS,
                                 auth=self.auth,
                                 data=json.dumps(document))
        return json.loads(response.content)

    def add_documents(self, documents: List[Dict]):
        """
           Add documents to storage using Elastic API bulk.

            :param documents: List of documents to be stored
            :return:
        """
        response = requests.post(url=f"{self.host}/{self.index}/_bulk",
                                 headers=BASIC_HEADERS,
                                 auth=self.auth,
                                 data='\n'.join(json.dumps(document) for document in documents) + '\n')
        return json.loads(response.content)

    def query(self, query: Dict):
        """
            Query storage using Elastic API query parameters.

        :param query: Elastic API query
        :return:
        """
        response = requests.get(url=f"{self.host}/{self.index}/_search",
                                headers=BASIC_HEADERS,
                                auth=self.auth,
                                data=json.dumps(query))
        return json.loads(response.content)
