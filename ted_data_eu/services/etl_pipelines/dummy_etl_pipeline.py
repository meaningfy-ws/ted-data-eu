import pathlib
from typing import Dict

from ted_data_eu import config
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC


class DummyETLPipeline(ETLPipelineABC):

    def extract(self) -> Dict:
        print(f"extract: {config.BQ_PATHS['q1']}")
        print(pathlib.Path(config.BQ_PATHS['q1']).read_text(encoding="utf-8"))
        return {"data": "hello"}

    def transform(self, extracted_data: Dict) -> Dict:
        print(f"transform: {extracted_data['data']}")
        return {"data": "transformed_hello"}

    def load(self, transformed_data: Dict):
        print(f"load: {transformed_data['data']}")


class TestETLPipeline(ETLPipelineABC):

    def extract(self) -> Dict:
        print("extract: HELLO1")
        return {"data": "hello1"}

    def transform(self, extracted_data: Dict) -> Dict:
        print(f"transform: {extracted_data['data']}")
        return {"data": "transformed_hello1"}

    def load(self, transformed_data: Dict):
        print(f"load: {transformed_data['data']}")