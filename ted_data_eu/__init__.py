import json
import pathlib
from typing import Dict

import dotenv
from ted_sws import TedConfigResolver, env_property, AirflowAndEnvConfigResolver

dotenv.load_dotenv(verbose=True, override=True)

PROJECT_RESOURCES_PATH = pathlib.Path(__file__).parent.resolve() / "resources"
PROJECT_RESOURCES_BQ_FOLDER_PATH = PROJECT_RESOURCES_PATH / "sparql_queries"
PROJECT_RESOURCES_POSTGRES_TABLES_PATH = PROJECT_RESOURCES_BQ_FOLDER_PATH / "postgres_tables"


class CommonConfig:

    @env_property()
    def DOMAIN(self, config_value: str) -> str:
        return config_value

    @env_property()
    def SUBDOMAIN(self, config_value: str) -> str:
        return config_value


class MasterDataRegistryAPIConfig:

    @env_property()
    def MASTER_DATA_REGISTRY_API_URL(self, config_value: str) -> str:
        return config_value

    @env_property()
    def MASTER_DATA_REGISTRY_API_USER(self, config_value: str) -> str:
        return config_value

    @env_property()
    def MASTER_DATA_REGISTRY_API_PASSWORD(self, config_value: str) -> str:
        return config_value


class PostgresTablesConfig:

    @property
    def TRIPLE_STORE_TABLE_QUERY_PATHS(self) -> Dict:
        query_paths = PROJECT_RESOURCES_POSTGRES_TABLES_PATH / "triple_store_queries"
        query_paths_map = {}
        for query_path in query_paths.iterdir():
            if query_path.is_file():
                query_paths_map[query_path.stem] = query_path
        return query_paths_map

    @property
    def CELLAR_TABLE_QUERY_PATHS(self) -> Dict:
        query_paths = PROJECT_RESOURCES_POSTGRES_TABLES_PATH / "cellar_queries"
        query_paths_map = {}
        for query_path in query_paths.iterdir():
            if query_path.is_file():
                query_paths_map[query_path.stem] = query_path
        return query_paths_map

    @property
    def TABLES_METADATA(self) -> Dict:
        tables_metadata_path = PROJECT_RESOURCES_POSTGRES_TABLES_PATH / "tables_metadata.json"
        return json.loads(tables_metadata_path.read_text(encoding='utf-8'))

    @env_property()
    def POSTGRES_TDA_DB_USER(self, config_value: str) -> str:
        return config_value

    @env_property()
    def POSTGRES_TDA_DB_PASSWORD(self, config_value: str) -> str:
        return config_value

    @env_property()
    def POSTGRES_TDA_DB_NAME(self, config_value: str) -> str:
        return config_value

    @env_property()
    def POSTGRES_TDA_DB_PORT(self, config_value: str) -> str:
        return config_value

    @env_property()
    def POSTGRES_HOST(self, config_value: str) -> str:
        return config_value


class BQResourcesConfig:

    @property
    def BQ_PATHS(self) -> Dict:
        bq_paths = PROJECT_RESOURCES_BQ_FOLDER_PATH
        bq_paths_map = {}
        for bq_path in bq_paths.iterdir():
            if bq_path.is_file():
                bq_paths_map[bq_path.stem] = bq_path
        return bq_paths_map


class GraphDBConfig:

    @env_property(config_resolver_class=AirflowAndEnvConfigResolver)
    def GRAPHDB_USER(self, config_value: str) -> str:
        return config_value

    @env_property(config_resolver_class=AirflowAndEnvConfigResolver)
    def GRAPHDB_PASSWORD(self, config_value: str) -> str:
        return config_value

    @env_property(config_resolver_class=AirflowAndEnvConfigResolver)
    def GRAPHDB_HOST(self, config_value: str) -> str:
        return config_value


class ElasticConfig:

    @env_property()
    def ELASTIC_USER(self, config_value: str) -> str:
        return config_value

    @env_property()
    def ELASTIC_PASSWORD(self, config_value: str) -> str:
        return config_value

    @env_property()
    def ELASTIC_VERSION(self, config_value: str) -> str:
        return config_value

    @env_property()
    def ELASTIC_HOST(self, config_value: str) -> str:
        return config_value

    @env_property()
    def ELASTIC_DEFAULT_INDEX(self, config_value: str) -> str:
        return config_value


class GitHubConfig:

    @env_property()
    def GITHUB_TOKEN(self, config_value: str) -> str:
        return config_value

    @env_property()
    def GITHUB_USERNAME(self, config_value: str) -> str:
        return config_value

    @env_property()
    def GITHUB_TED_DATA_ARTEFACTS_URL(self, config_value: str) -> str:
        return config_value


class TedDataConfigResolver(TedConfigResolver, BQResourcesConfig, GraphDBConfig, ElasticConfig, PostgresTablesConfig,
                            CommonConfig, MasterDataRegistryAPIConfig, GitHubConfig):
    """
        This class is used for automatic config discovery.
    """


config = TedDataConfigResolver()
