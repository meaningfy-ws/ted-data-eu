import pathlib

RESOURCES_PATH = pathlib.Path(__file__).parent.resolve()
GRAPHDB_REPOSITORY_CONFIG_PATH =  RESOURCES_PATH / "graphdb_repository_config"
GRAPHDB_REPOSITORY_CONFIG_FILE = GRAPHDB_REPOSITORY_CONFIG_PATH / "repository_config.json"