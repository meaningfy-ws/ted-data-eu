import pathlib

RESOURCE_DIR_PATH = pathlib.Path(__file__).parent.resolve()

OPEN_TENDER_JSONS = RESOURCE_DIR_PATH / "open_tender_all_jsons"
OPEN_TENDER_EXTRACTION_OUTPUT = RESOURCE_DIR_PATH / "open_tender_extraction_output"