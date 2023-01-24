from datetime import datetime
from typing import Dict

import numpy as np
from pymongo import MongoClient
from ted_sws.data_manager.adapters.triple_store import FusekiAdapter, TripleStoreABC

from ted_data_eu import config
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC
from ted_data_eu.services.currency_convertor import convert_currency

DEFAULT_FUSEKI_DATASET_NAME = 'ted_data_dataset'  # TODO: temporary while not put in config resolver
TED_DATA_MONGODB_DATABASE_NAME = 'ted_analytics'  # TODO: temporary while not put in config resolver


class PotentialCustomersETLPipeline(ETLPipelineABC):

    def __init__(self, triple_store: TripleStoreABC = None, mongo_client: MongoClient = None, query_limit: int = None):
        self.triple_store = triple_store if triple_store else FusekiAdapter(host=config.FUSEKI_ADMIN_HOST,
                                                                            user=config.FUSEKI_ADMIN_USER,
                                                                            password=config.FUSEKI_ADMIN_PASSWORD)
        self.mongo_client = mongo_client if mongo_client else MongoClient(config.MONGO_DB_AUTH_URL)
        self.query_limit = query_limit

    def extract(self) -> Dict:
        triple_store_endpoint = self.triple_store.get_sparql_triple_store_endpoint(DEFAULT_FUSEKI_DATASET_NAME)
        query = config.BQ_POTENTIAL_CUSTOMERS.read_text(encoding='utf-8')
        if self.query_limit:
            query += f" LIMIT {str(self.query_limit)}"
        query_result = triple_store_endpoint.with_query(query).fetch_tabular()
        return {"data": query_result}

    def transform(self, extracted_data: Dict) -> Dict:
        extracted_data = extracted_data['data']
        extracted_data['CustomerEmail'] = extracted_data['CustomerEmail'].astype("string")
        extracted_data['CustomerName'] = extracted_data['CustomerName'].astype("string")
        extracted_data['ContractTitle'] = extracted_data['ContractTitle'].astype("string")
        extracted_data['LotCPV'] = extracted_data['LotCPV'].astype("string")
        extracted_data['ContractConclusionDate'] = extracted_data['ContractConclusionDate'].astype("string")
        extracted_data['Currency'] = extracted_data['Currency'].astype("string")
        extracted_data['LotCPV'] = extracted_data['LotCPV'].str.split('/').str[-1]
        extracted_data['Currency'] = extracted_data['Currency'].str.split('/').str[-1]
        extracted_data = extracted_data.groupby('ContractTitle', as_index=False).agg(
            {
                "CustomerEmail": "first",
                "CustomerName": "first",
                "LotCPV": lambda x: ','.join(x),
                "ContractConclusionDate": "first",
                "TotalValue": "first",
                "Currency": "first",

            }
        )
        extracted_data["EuroCurrency"] = extracted_data[['TotalValue', 'Currency', 'ContractConclusionDate']].apply(
            lambda x: convert_currency(x[0], x[1], datetime.strptime(x[2], '%Y-%m-%d').date()), axis=1)
        extracted_data["EuroCurrency"] = extracted_data["EuroCurrency"].apply(lambda x: round(x, 2) if x else None)
        extracted_data = extracted_data.replace({np.nan: None})
        return {"data": extracted_data}

    def load(self, transformed_data: Dict):
        transformed_data = transformed_data['data']

        mongodb_database = self.mongo_client[TED_DATA_MONGODB_DATABASE_NAME]
        query_collection = mongodb_database[config.BQ_POTENTIAL_CUSTOMERS.stem]
        query_collection.drop()
        if not transformed_data.empty:
            for row in transformed_data.itertuples():
                query_collection.insert_one(row._asdict())
