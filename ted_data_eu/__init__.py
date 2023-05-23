import pathlib
from typing import Dict

from ted_sws import TedConfigResolver, env_property, AirflowAndEnvConfigResolver
import dotenv

dotenv.load_dotenv(verbose=True, override=True)

PROJECT_RESOURCES_PATH = pathlib.Path(__file__).parent.resolve() / "resources"
PROJECT_RESOURCES_BQ_FOLDER_PATH = PROJECT_RESOURCES_PATH / "sparql_queries"


class CommonConfig:

    @env_property()
    def DOMAIN(self, config_value: str) -> str:
        return config_value

    @env_property()
    def SUBDOMAIN(self, config_value: str) -> str:
        return config_value


class PostgresTablesConfig:

    @property
    def TABLE_QUERY_PATHS(self) -> Dict:
        query_paths = PROJECT_RESOURCES_BQ_FOLDER_PATH / "postgres_tables"
        query_paths_map = {}
        for query_path in query_paths.iterdir():
            if query_path.is_file():
                query_paths_map[query_path.stem] = query_path
        return query_paths_map

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


class TedDataConfigResolver(TedConfigResolver, BQResourcesConfig, GraphDBConfig, ElasticConfig, PostgresTablesConfig,
                            CommonConfig):
    """
        This class is used for automatic config discovery.
    """


config = TedDataConfigResolver()
