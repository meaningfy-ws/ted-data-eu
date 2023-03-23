import pathlib
from datetime import datetime, date
from string import Template
from typing import Dict

import pandas as pd
from dateutil import rrule

from ted_data_eu import config
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC
from ted_data_eu.adapters.storage import ElasticStorage
from ted_data_eu.adapters.triple_store import GraphDBAdapter
from ted_data_eu.services.data_load_service import load_documents_to_storage

TED_DATA_ETL_PIPELINE_NAME = "ted_data"
START_DATE_METADATA_FIELD = "start_date"
END_DATE_METADATA_FIELD = "end_date"
TRIPLE_STORE_ENDPOINT = "notices"

PROCEDURE_TYPE_COLUMN_NAME = "procedure_type"
WINNER_NUTS_COLUMN_NAME = "winner_nuts"
LOT_NUTS_COLUMN_NAME = "lot_nuts_code"
CURRENCY_COLUMN_NAME = "currency"
PUBLICATION_DATE_COLUMN_NAME = "publication_date"
WINNER_NAME_COLUMN_NAME = "winner_name"
AMMOUNT_VALUE_COLUMN_NAME = "ammount_value"
PROCEDURE_TITLE_COLUMN_NAME = "procedure_title"

def generate_dates_by_date_range(start_date: str, end_date: str) -> list:
    """
        Given a date range returns all daily dates in that range
    :param start_date:
    :param end_date:
    :return:
    """
    return [dt.strftime('%Y%m%d')
            for dt in rrule.rrule(rrule.DAILY,
                                  dtstart=datetime.strptime(start_date, '%Y%m%d'),
                                  until=datetime.strptime(end_date, '%Y%m%d'))]


def generate_sparql_filter_by_date_range(start_date: str, end_date: str) -> str:
    date_range = generate_dates_by_date_range(start_date, end_date)
    result_string = list(map(lambda x: f"\"{x}\"", date_range))

    return " ".join(result_string)


class TedDataETLPipeline(ETLPipelineABC):

    def __init__(self):
        self.etl_metadata = {}
        self.pipeline_name = TED_DATA_ETL_PIPELINE_NAME

    def get_pipeline_name(self) -> str:
        return self.pipeline_name

    def set_metadata(self, etl_metadata: dict):
        self.etl_metadata = etl_metadata

    def get_metadata(self) -> dict:
        return self.etl_metadata

    def extract(self) -> Dict:
        etl_metadata = self.get_metadata()
        etl_metadata_fields = etl_metadata.keys()
        if START_DATE_METADATA_FIELD in etl_metadata_fields and END_DATE_METADATA_FIELD in etl_metadata_fields:
            date_range = generate_sparql_filter_by_date_range(etl_metadata[START_DATE_METADATA_FIELD], etl_metadata[END_DATE_METADATA_FIELD])
        else:
            date_range = date.today().strftime("\"%Y%m%d\"")

        sparql_query_template = Template(config.BQ_PATHS[TED_DATA_ETL_PIPELINE_NAME].read_text(encoding='utf-8'))
        sparql_query_str = sparql_query_template.substitute(date_range=date_range)
        triple_store_endpoint = GraphDBAdapter().get_sparql_triple_store_endpoint(repository_name=TRIPLE_STORE_ENDPOINT)
        result_table = triple_store_endpoint.with_query(sparql_query_str).fetch_tabular()
        return {"data": result_table}

    def transform(self, extracted_data: Dict) -> Dict:
        data_table = extracted_data['data']
        data_table[WINNER_NUTS_COLUMN_NAME] = data_table[WINNER_NUTS_COLUMN_NAME].apply(lambda x: x.split('/')[-1])
        data_table[PROCEDURE_TYPE_COLUMN_NAME] = data_table[PROCEDURE_TYPE_COLUMN_NAME].apply(lambda x: x.split('/')[-1])
        data_table[LOT_NUTS_COLUMN_NAME] = data_table[LOT_NUTS_COLUMN_NAME].apply(lambda x: x.split('/')[-1])
        data_table[CURRENCY_COLUMN_NAME] = data_table[CURRENCY_COLUMN_NAME].apply(lambda x: x.split('/')[-1])
        data_table[PROCEDURE_TITLE_COLUMN_NAME] = data_table[PROCEDURE_TITLE_COLUMN_NAME].apply(lambda x: x.strip())
        data_table[PUBLICATION_DATE_COLUMN_NAME] = data_table[PUBLICATION_DATE_COLUMN_NAME].apply(lambda x: pd.to_datetime(str(x), format='%Y%m%d'))
        return {"data": data_table}

    def load(self, transformed_data: Dict):
        elastic_storage = ElasticStorage(elastic_index=TED_DATA_ETL_PIPELINE_NAME)
        data_table = transformed_data['data']
        documents = []
        for index, row in data_table.iterrows():
            documents.append(
                {
                    PUBLICATION_DATE_COLUMN_NAME: row[PUBLICATION_DATE_COLUMN_NAME],
                    WINNER_NAME_COLUMN_NAME: row[WINNER_NAME_COLUMN_NAME],
                    WINNER_NUTS_COLUMN_NAME: row[WINNER_NUTS_COLUMN_NAME],
                    AMMOUNT_VALUE_COLUMN_NAME: row[AMMOUNT_VALUE_COLUMN_NAME],
                    CURRENCY_COLUMN_NAME: row[CURRENCY_COLUMN_NAME],
                    PROCEDURE_TITLE_COLUMN_NAME: row[PROCEDURE_TITLE_COLUMN_NAME],
                    LOT_NUTS_COLUMN_NAME: row[LOT_NUTS_COLUMN_NAME],
                    PROCEDURE_TYPE_COLUMN_NAME: row[PROCEDURE_TYPE_COLUMN_NAME]
                }
            )
        load_documents_to_storage(documents=documents, storage=elastic_storage)
