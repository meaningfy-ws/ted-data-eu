import logging
from datetime import datetime, date, timedelta
from string import Template
from typing import Dict

import pandas as pd
from dateutil import rrule
from pandas import DataFrame

from ted_data_eu import config
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC
from ted_data_eu.adapters.storage import ElasticStorage
from ted_data_eu.adapters.triple_store import GraphDBAdapter
from ted_data_eu.services.currency_convertor import convert_currency
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
AMOUNT_VALUE_COLUMN_NAME = "ammount_value"
PROCEDURE_TITLE_COLUMN_NAME = "procedure_title"
LOT_URL_COLUMN_NAME = 'lot'
BUYER_NAME_COLUMN_NAME = 'buyer_name'
LOT_CPV_COLUMN_NAME = 'lot_cpv'

AMOUNT_VALUE_EUR_COLUMN_NAME = 'amount_value_eur'

TED_DATA_COLUMNS = [
    PROCEDURE_TYPE_COLUMN_NAME,
    WINNER_NUTS_COLUMN_NAME,
    LOT_NUTS_COLUMN_NAME,
    CURRENCY_COLUMN_NAME,
    PUBLICATION_DATE_COLUMN_NAME,
    WINNER_NAME_COLUMN_NAME,
    AMOUNT_VALUE_COLUMN_NAME,
    PROCEDURE_TITLE_COLUMN_NAME,
    LOT_URL_COLUMN_NAME,
    BUYER_NAME_COLUMN_NAME,
    LOT_CPV_COLUMN_NAME
]

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
    """
        Given a date range returns all daily dates in string format for sparql query
    :param start_date:
    :param end_date:
    :return:
    """
    date_range = generate_dates_by_date_range(start_date, end_date)
    result_string = list(map(lambda x: f"\"{x}\"", date_range))

    return " ".join(result_string)


class TedETLException(Exception):
    """
        TedData ETL Exception
    """
    pass


class TedDataETLPipeline(ETLPipelineABC):
    """
        ETL Class that gets data from TDA endpoint, transforms and inserts result to document storage
    """

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
            if START_DATE_METADATA_FIELD == END_DATE_METADATA_FIELD:
                date_range = datetime.strptime(START_DATE_METADATA_FIELD, "\"%Y%m%d\"")
                logging.info("Querying data from one day")
            else:
                date_range = generate_sparql_filter_by_date_range(etl_metadata[START_DATE_METADATA_FIELD],
                                                                  etl_metadata[END_DATE_METADATA_FIELD])
                logging.info("Querying data from date range")
        else:
            logging.info("Querying data from yesterday")
            date_range = (date.today() - timedelta(days=1)).strftime("\"%Y%m%d\"")

        sparql_query_template = Template(config.BQ_PATHS[TED_DATA_ETL_PIPELINE_NAME].read_text(encoding='utf-8'))
        sparql_query_str = sparql_query_template.substitute(date_range=date_range)
        triple_store_endpoint = GraphDBAdapter().get_sparql_triple_store_endpoint(repository_name=TRIPLE_STORE_ENDPOINT)
        result_table = triple_store_endpoint.with_query(sparql_query_str).fetch_tabular()
        return {"data": result_table}

    def transform(self, extracted_data: Dict) -> Dict:
        data_table: DataFrame = extracted_data['data']
        # columns_wihtout_date = TED_DATA_COLUMNS.copy()
        # columns_wihtout_date.remove(PUBLICATION_DATE_COLUMN_NAME)
        # data_table.dropna(subset=columns_wihtout_date, how='all', inplace=True)
        if data_table.empty:
            raise TedETLException("No data was been fetched from triple store!")
        else:
            logging.info(data_table.head())

        data_table = data_table.astype({
            WINNER_NUTS_COLUMN_NAME: str,
            PROCEDURE_TYPE_COLUMN_NAME: str,
            LOT_NUTS_COLUMN_NAME: str,
            CURRENCY_COLUMN_NAME: str,
            LOT_CPV_COLUMN_NAME: str,
            PROCEDURE_TITLE_COLUMN_NAME: str
        })


        aggregations = dict.fromkeys(data_table, 'first')
        aggregations[BUYER_NAME_COLUMN_NAME] = lambda x: list(x)
        del aggregations[LOT_URL_COLUMN_NAME]

        data_table = data_table.groupby(LOT_URL_COLUMN_NAME).agg(aggregations).reset_index()

        data_table[WINNER_NUTS_COLUMN_NAME] = data_table[WINNER_NUTS_COLUMN_NAME].apply(
            lambda x: x.split('/')[-1] if x else x)
        data_table[PROCEDURE_TYPE_COLUMN_NAME] = data_table[PROCEDURE_TYPE_COLUMN_NAME].apply(
            lambda x: x.split('/')[-1] if x else x)
        data_table[LOT_NUTS_COLUMN_NAME] = data_table[LOT_NUTS_COLUMN_NAME].apply(
            lambda x: x.split('/')[-1] if x else x)
        data_table[CURRENCY_COLUMN_NAME] = data_table[CURRENCY_COLUMN_NAME].apply(
            lambda x: x.split('/')[-1] if x else x)
        data_table[LOT_CPV_COLUMN_NAME] = data_table[LOT_CPV_COLUMN_NAME].apply(
            lambda x: x.split('/')[-1] if x else x)
        data_table[PROCEDURE_TITLE_COLUMN_NAME] = data_table[PROCEDURE_TITLE_COLUMN_NAME].apply(
            lambda x: x.strip() if x else x)
        data_table[PUBLICATION_DATE_COLUMN_NAME] = data_table[PUBLICATION_DATE_COLUMN_NAME].apply(
            lambda x: pd.to_datetime(str(x), format='%Y%m%d') if x else x)

        data_table[AMOUNT_VALUE_EUR_COLUMN_NAME] = data_table.apply(lambda x: x[AMOUNT_VALUE_COLUMN_NAME] if x[CURRENCY_COLUMN_NAME] == 'EUR' else convert_currency(
            amount=x[AMOUNT_VALUE_COLUMN_NAME],
            currency=x[CURRENCY_COLUMN_NAME],
            new_currency='EUR',
            date=x[PUBLICATION_DATE_COLUMN_NAME].date()
        ), axis=1)

        return {"data": data_table}

    def load(self, transformed_data: Dict):
        elastic_storage = ElasticStorage(elastic_index=TED_DATA_ETL_PIPELINE_NAME)
        data_table = transformed_data['data']
        documents = []
        for row_index, row in data_table.iterrows():
            row_dict = {}
            for column_name, value in row.items():
                row_dict[column_name] = value
            # Using Lot URL as unique id
            row_dict['_id'] = getattr(row, LOT_URL_COLUMN_NAME)
            documents.append(row_dict)
        load_documents_to_storage(documents=documents, storage=elastic_storage)
