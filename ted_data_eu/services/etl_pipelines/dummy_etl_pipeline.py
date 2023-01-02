from typing import Dict

from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC


class DummyETLPipeline(ETLPipelineABC):

    def extract(self) -> Dict:
        print("extract: HELLO")
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