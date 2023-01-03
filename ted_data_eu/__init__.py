import pathlib
from typing import Dict

from ted_sws import TedConfigResolver

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


class TedDataConfigResolver(TedConfigResolver, BQResourcesConfig):
    """
        This class is used for automatic config discovery.
    """


config = TedDataConfigResolver()
