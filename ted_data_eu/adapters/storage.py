from typing import Dict, List
from ted_data_eu import config
from ted_data_eu.adapters.storage_abc import DocumentStorageABC
from elasticsearch import Elasticsearch, helpers


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
        host = host or config.ELASTIC_HOST
        basic_auth = (user or config.ELASTIC_USER, password or config.ELASTIC_PASSWORD)
        self.es_client = Elasticsearch(hosts=[f"{host}:443"], basic_auth=basic_auth)
        self.elastic_index = elastic_index
        if not self.es_client.indices.exists(index=self.elastic_index):
            self.es_client.indices.create(index=self.elastic_index)

    def add_document(self, document: Dict):
        """
           Add document to storage.

            :param document: Document to be stored
            :return:
        """
        response = self.es_client.index(index=self.elastic_index, document=document)
        if not response:
            raise ElasticStorageException(str(response))
        self.es_client.indices.refresh(index=self.elastic_index)

    def add_documents(self, documents: List[Dict]):
        """
           Add documents to storage using Elastic API bulk.

            :param documents: List of documents to be stored
            :return:
        """
        results = helpers.parallel_bulk(self.es_client, documents, index=self.elastic_index)
        for result in results:
            if not result[0]:
                raise ElasticStorageException(str(result[1]))
        self.es_client.indices.refresh(index=self.elastic_index)

    def clear(self):
        """
            Delete current index.

        :return:
        """
        response = self.es_client.delete_by_query(index=self.elastic_index, body={"query": {"match_all": {}}})
        if not response:
            raise ElasticStorageException(str(response))
        self.es_client.indices.refresh(index=self.elastic_index)

    def count(self) -> int:
        """
            Return number of documents from current ElasticSearch Index.

        :return:
        """
        response = self.es_client.count(index=self.elastic_index)
        if response:
            return response["count"]
        else:
            raise ElasticStorageException(str(response))

    def query(self, query) -> List[dict]:
        """
            Return list of documents based on result of query in ElasticSearch Index.
        :param query:
        :return:
        """
        self.es_client.indices.refresh(index=self.elastic_index)
        response = self.es_client.search(index=self.elastic_index, query=query)
        if response:
            return [document_hit["_source"] for document_hit in response['hits']['hits']]
        else:
            raise ElasticStorageException(str(response))
