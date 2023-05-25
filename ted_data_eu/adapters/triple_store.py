import io
import json
from pathlib import Path
from typing import Union
from urllib.parse import urljoin

import rdflib
import requests
from SPARQLWrapper import CSV
from ted_sws.data_manager.adapters.sparql_endpoint import SPARQLTripleStoreEndpoint, TripleStoreEndpointABC, \
    DEFAULT_ENCODING
from ted_sws.data_manager.adapters.triple_store import TripleStoreABC, RDF_MIME_TYPES

from ted_data_eu import config
from ted_data_eu.resources import GRAPHDB_REPOSITORY_CONFIG_FILE

REPOSITORY_ID = "id"


class GraphDBException(Exception):
    """
        An exception when GraphDB server interaction has failed.
    """


class TDATripleStoreEndpointABC(SPARQLTripleStoreEndpoint):
    """
        This class provides an abstraction for a TDA TripleStore based on SPARQLTripleStoreEndpoint.
    """

    def fetch_csv(self) -> io.StringIO:
        """
        Get query results in a CSV format
        :return:
        """
        if not self.endpoint.queryString or self.endpoint.queryString.isspace():
            raise Exception("The query is empty.")

        self.endpoint.setReturnFormat(CSV)
        query_result = self.endpoint.queryAndConvert()
        return io.StringIO(str(query_result, encoding=DEFAULT_ENCODING))


class GraphDBAdapter(TripleStoreABC):
    def __init__(self, host: str = None,
                 user: str = None,
                 password: str = None):

        self.host = host if host else config.GRAPHDB_HOST
        self.user = user if user else config.GRAPHDB_USER
        self.password = password if password else config.GRAPHDB_PASSWORD
        response = requests.post(urljoin(self.host, f"/rest/login/{self.user}"),
                                 headers={"X-GraphDB-Password": self.password})
        if response.status_code != 200:
            raise GraphDBException(response.text)
        self.headers = {'Authorization': response.headers.get('Authorization')}

    def create_repository(self, repository_name: str):
        """
            Create the dataset for the Fuseki store
        :param repository_name: The repository identifier. This should be short alphanumeric string uniquely
        identifying the repository
        :return: true if repository was created
        """
        if not repository_name:
            raise GraphDBException('Repository name cannot be empty.')

        headers = {**self.headers, 'Accept': 'application/json',
                   "content-type": "application/json;charset=UTF-8"}
        repository_configs = json.loads(GRAPHDB_REPOSITORY_CONFIG_FILE.read_text(encoding="utf-8"))
        repository_configs[REPOSITORY_ID] = repository_name
        response = requests.post(urljoin(self.host, '/rest/repositories'), headers=headers,
                                 data=json.dumps(repository_configs))
        if response.status_code != 201:
            raise GraphDBException(response.text)

    def add_data_to_repository(self, file_content: Union[str, bytes, bytearray], mime_type: str, repository_name: str):
        update_url = urljoin(self.host, f"/repositories/{repository_name}/statements")
        headers = {**self.headers, "Content-Type": mime_type}
        response = requests.post(url=update_url, data=file_content, headers=headers)
        if response.status_code != 204:
            raise GraphDBException(response.text)

    def add_file_to_repository(self, file_path: Path, repository_name: str):
        file_content = file_path.open('rb').read()
        file_format = rdflib.util.guess_format(str(file_path))
        mime_type = RDF_MIME_TYPES[file_format] if file_format in RDF_MIME_TYPES else "text/n3"
        self.add_data_to_repository(file_content=file_content, mime_type=mime_type, repository_name=repository_name)

    def delete_repository(self, repository_name: str):
        """
            Delete the repository from the Fuseki store
        :param repository_name: The repository identifier. This should be short alphanumeric string uniquely
        identifying the repository
        :return: true if repository was deleted
        """
        response = requests.delete(urljoin(self.host, f"/rest/repositories/{repository_name}"), headers=self.headers)
        if response.status_code != 200:
            raise GraphDBException(response.text)

    def list_repositories(self) -> list:
        """
            Get the list of the repository names from the Fuseki store.
        :return: the list of the repository names
        :rtype: list
        """
        response = requests.get(urljoin(self.host, '/rest/repositories'), headers=self.headers)
        if response.status_code != 200:
            raise GraphDBException(response.text)
        repositories = json.loads(response.text)
        return [repository[REPOSITORY_ID] for repository in repositories]

    def get_sparql_triple_store_endpoint_url(self, repository_name: str) -> str:
        """
            Helper method to create the url for querying.
        :param repository_name:
        :return:
        """
        return urljoin(self.host, f"/repositories/{repository_name}")

    def get_sparql_triple_store_endpoint(self, repository_name: str = None) -> TripleStoreEndpointABC:
        """
            Helper method to create the triple store endpoint for querying.
        :param repository_name: The dataset identifier. This should be short alphanumeric string uniquely
        identifying the repository
        :return: the query url
        """
        endpoint_url = self.get_sparql_triple_store_endpoint_url(repository_name=repository_name)
        sparql_endpoint = SPARQLTripleStoreEndpoint(endpoint_url=endpoint_url, user=self.user, password=self.password)
        return sparql_endpoint

    def get_sparql_tda_triple_store_endpoint(self, repository_name: str = None) -> TDATripleStoreEndpointABC:
        """
            Helper method to create the TDA triple store endpoint for querying.
        :param repository_name: The dataset identifier. This should be short alphanumeric string uniquely
        identifying the repository
        :return: the query url
        """
        endpoint_url = self.get_sparql_triple_store_endpoint_url(repository_name=repository_name)
        sparql_endpoint = TDATripleStoreEndpointABC(endpoint_url=endpoint_url, user=self.user, password=self.password)
        return sparql_endpoint
