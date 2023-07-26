from pathlib import Path
from typing import Dict

import pandas as pd
from ted_sws.data_manager.adapters.triple_store import TripleStoreABC

from ted_data_eu import config
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC
from ted_data_eu.adapters.storage import MongoDBStorage
from ted_data_eu.adapters.storage_abc import DocumentStorageABC
from ted_data_eu.adapters.triple_store import GraphDBAdapter

EDA_COLLECTION_NAME = "tda_eda"
EDA_PIPELINE_NAME = "tda_eda_pipeline"
DATA_FIELD = "eda_data"
TRIPLE_STORE_ENDPOINT = "notices"


class EDAETLPipeline(ETLPipelineABC):

    def __init__(self,
                 triple_store_adapter: TripleStoreABC = None,
                 document_db_adapter: DocumentStorageABC = None,
                 triple_store_queries_path: Path = None):
        self.document_db_adapter = document_db_adapter or MongoDBStorage(
            database_name=config.MONGO_DB_AGGREGATES_DATABASE_NAME,
            collection_name=EDA_COLLECTION_NAME,
            mongo_auth_url=config.MONGO_DB_AUTH_URL)
        self.triple_store_adapter = triple_store_adapter or GraphDBAdapter(host=config.GRAPHDB_HOST,
                                                                           user=config.GRAPHDB_USER,
                                                                           password=config.GRAPHDB_PASSWORD)
        self.metadata = None
        self.triple_store_queries_path = triple_store_queries_path or config.EDA_TRIPLE_STORE_QUERIES_PATHS

    def get_pipeline_name(self) -> str:
        return EDA_PIPELINE_NAME

    def set_metadata(self, etl_metadata: dict):
        self.metadata = etl_metadata

    def get_metadata(self) -> dict:
        return self.metadata

    def extract(self) -> Dict:
        example_query: str = self.triple_store_queries_path["test_query"].read_text()
        result_table: pd.DataFrame = self.triple_store_adapter.get_sparql_triple_store_endpoint(
            repository_name=TRIPLE_STORE_ENDPOINT).with_query(
            example_query).fetch_tabular()
        return {DATA_FIELD: result_table}

    def transform(self, extracted_data: Dict) -> Dict:
        data_table: pd.DataFrame = extracted_data[DATA_FIELD]
        data_json = data_table.to_dict(orient="records")
        return {DATA_FIELD: data_json}

    def load(self, transformed_data: Dict):
        data_to_load = transformed_data[DATA_FIELD]
        self.document_db_adapter.add_documents(data_to_load)


# if __name__ == '__main__':
#     eda_pipeline = EDAETLPipeline()
#     data = eda_pipeline.extract()
#     data = eda_pipeline.transform(data)
#     eda_pipeline.load(data)
