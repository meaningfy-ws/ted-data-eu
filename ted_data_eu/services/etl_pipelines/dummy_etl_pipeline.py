import pathlib
from typing import Dict

from dags.etl_executor import TED_DATA_ETL_PIPELINE_NAME
from ted_data_eu import config
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC
from ted_data_eu.adapters.triple_store import GraphDBAdapter




class DummyETLPipeline(ETLPipelineABC):

    def __init__(self):
        self.etl_metadata = {}
        self.pipeline_name = "dummy_pipeline"

    def get_pipeline_name(self) -> str:
        return self.pipeline_name

    def set_metadata(self, etl_metadata: dict):
        self.etl_metadata = etl_metadata

    def get_metadata(self) -> dict:
        return self.etl_metadata

    def extract(self) -> Dict:
        etl_metadata = self.get_metadata()
        self.etl_metadata = {}
        print(etl_metadata)
        return {"data": "hello"}

    def transform(self, extracted_data: Dict) -> Dict:
        print(f"transform: {extracted_data['data']}")
        return {"data": "transformed_hello"}

    def load(self, transformed_data: Dict):
        print(f"load: {transformed_data['data']}")


class TestETLPipeline(ETLPipelineABC):

    def get_pipeline_name(self) -> str:
        return "test_etl_pipeline"

    def set_metadata(self, etl_metadata: dict):
        pass

    def get_metadata(self) -> dict:
        return None

    def extract(self) -> Dict:
        print("extract: HELLO1")
        return {"data": "hello1"}

    def transform(self, extracted_data: Dict) -> Dict:
        print(f"transform: {extracted_data['data']}")
        return {"data": "transformed_hello1"}

    def load(self, transformed_data: Dict):
        print(f"load: {transformed_data['data']}")
