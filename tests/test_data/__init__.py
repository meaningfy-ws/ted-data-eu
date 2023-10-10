import pathlib

TEST_DATA_PATH = pathlib.Path(__file__).parent.resolve()

TEST_RDF_MANIFESTATIONS_PATH = TEST_DATA_PATH / "rdf_manifestations"

TEST_DOCUMENTS_PATH = TEST_DATA_PATH / "documents"

TEST_NOTICES_PATH = TEST_DATA_PATH / "notices"

TEST_DEDUPLICATION_DIR_PATH = TEST_DATA_PATH / "deduplication_data"

TEST_ORGANIZATION_DEDUPLICATION_DATA_PATH = TEST_DEDUPLICATION_DIR_PATH / "organization_deduplication.csv"
