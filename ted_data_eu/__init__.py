import pathlib
from typing import Dict

from ted_sws import TedConfigResolver, env_property
import dotenv

dotenv.load_dotenv(verbose=True, override=True)

PROJECT_RESOURCES_PATH = pathlib.Path(__file__).parent.resolve() / "resources"
PROJECT_RESOURCES_BQ_FOLDER_PATH = PROJECT_RESOURCES_PATH / "sparql_queries"


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

    @env_property()
    def GRAPHDB_USER(self, config_value: str) -> str:
        return config_value

    @env_property()
    def GRAPHDB_PASSWORD(self, config_value: str) -> str:
        return config_value

    @env_property()
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


class TedDataConfigResolver(TedConfigResolver, BQResourcesConfig, GraphDBConfig, ElasticConfig):
    """
        This class is used for automatic config discovery.
    """


config = TedDataConfigResolver()
