import re
from pathlib import Path
from typing import Dict, Optional

import sqlalchemy
from pandas import DataFrame

from ted_data_eu import config
from ted_data_eu.adapters.cpv_processor import CPVProcessor, CPV_MAX_RANK, CPV_MIN_RANK
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC
from ted_data_eu.adapters.nuts_processor import NUTSProcessor, NUTS_MIN_RANK, NUTS_MAX_RANK
from ted_data_eu.adapters.triple_store import GraphDBAdapter
from ted_data_eu.services.currency_convertor import convert_currency, \
    get_last_available_date_for_currency

TED_NOTICES_LINK = 'https://ted.europa.eu/udl?uri=TED:NOTICE:{notice_id}:TEXT:EN:HTML'
TRIPLE_STORE_ENDPOINT = "notices"
POSTGRES_URL = f"postgresql://{config.POSTGRES_TDA_DB_USER}:{config.POSTGRES_TDA_DB_PASSWORD}@{config.SUBDOMAIN}{config.DOMAIN}:{config.POSTGRES_TDA_DB_PORT}/{config.POSTGRES_TDA_DB_NAME}"
EURO_CURRENCY_ID = "EUR"
SEND_CHUNK_SIZE = 1000

AMOUNT_VALUE_EUR_COLUMN = "AmountValueEUR"
AMOUNT_VALUE_COLUMN = "AmountValue"
CURRENCY_ID_COLUMN = "CurrencyId"
CONVERSION_TO_EUR_DATE_COLUMN = "ConversionToEURDate"

NOTICE_LINK_COLUMN = "NoticeLink"
NOTICE_ID_COLUMN = "NoticeId"

ORIGINAL_CPV_COLUMN = "OriginalCPV"
ORIGINAL_CPV_LABEL_COLUMN = "OriginalCPVLabel"
ORIGINAL_CPV_LEVEL_COLUMN = "OriginalCPVLevel"

NUTS_LABEL_COLUMN = "NUTSLabel"
NUTS_LEVEL_COLUMN = "NUTSLevel"
NUTS_ID_COLUMN = "NUTSId"


def transform_monetary_value_table(data_table: DataFrame) -> DataFrame:
    """
    Transforms monetary value table by converting all amounts to EUR and adding conversion date
    """
    data_table[AMOUNT_VALUE_EUR_COLUMN] = data_table.apply(
        lambda x: convert_currency(amount=x[AMOUNT_VALUE_COLUMN], currency=x[CURRENCY_ID_COLUMN],
                                   new_currency=EURO_CURRENCY_ID),
        axis=1)
    data_table[CONVERSION_TO_EUR_DATE_COLUMN] = data_table.apply(
        lambda x: get_last_available_date_for_currency(currency=x[CURRENCY_ID_COLUMN]), axis=1)

    return data_table


def transform_notice_table(data_table: DataFrame) -> DataFrame:
    """
    Transforms notice table by adding link to notice
    """
    data_table[NOTICE_LINK_COLUMN] = data_table.apply(
        lambda x: generate_link_to_notice(x[NOTICE_ID_COLUMN]), axis=1)

    return data_table


def transform_purpose_table(data_table: DataFrame) -> DataFrame:
    """
    Transforms purpose table by adding CPV codes and labels on all levels
    """
    cpv_processor = CPVProcessor()
    data_table[ORIGINAL_CPV_LABEL_COLUMN] = data_table.apply(
        lambda x: cpv_processor.get_cpv_label_by_code(x[ORIGINAL_CPV_COLUMN]), axis=1)
    data_table[ORIGINAL_CPV_LEVEL_COLUMN] = data_table.apply(
        lambda x: cpv_processor.get_cpv_rank(x[ORIGINAL_CPV_COLUMN]), axis=1)

    for cpv_lvl in range(CPV_MIN_RANK, CPV_MAX_RANK + 1):
        data_table[f"CPV{cpv_lvl}"] = data_table.apply(
            lambda x: cpv_processor.get_cpv_parent_code_by_rank(x[ORIGINAL_CPV_COLUMN], cpv_lvl), axis=1)
        data_table[f"CPV{cpv_lvl}Label"] = data_table.apply(
            lambda x: cpv_processor.get_cpv_label_by_code(x[f"CPV{cpv_lvl}"]), axis=1)

    return data_table


def transform_nuts_table(data_table: DataFrame) -> DataFrame:
    """
    Transforms nuts table by adding NUTS codes and labels on all levels
    """
    nuts_processor = NUTSProcessor()
    data_table[NUTS_LABEL_COLUMN] = data_table.apply(
        lambda x: nuts_processor.get_nuts_label_by_code(x[NUTS_ID_COLUMN]), axis=1)
    data_table[NUTS_LEVEL_COLUMN] = data_table.apply(
        lambda x: nuts_processor.get_nuts_level_by_code(x[NUTS_ID_COLUMN]), axis=1)

    for cpv_lvl in range(NUTS_MIN_RANK, NUTS_MAX_RANK + 1):
        data_table[f"NUTS{cpv_lvl}"] = data_table.apply(
            lambda x: nuts_processor.get_nuts_code_by_level(x[NUTS_ID_COLUMN], cpv_lvl), axis=1)
        data_table[f"NUTS{cpv_lvl}Label"] = data_table.apply(
            lambda x: nuts_processor.get_nuts_label_by_code(x[f"NUTS{cpv_lvl}"]), axis=1)

    return data_table


TRANSFORMED_TABLES = {
    "MonetaryValue": transform_monetary_value_table,
    "Notice": transform_notice_table,
    "Purpose": transform_purpose_table,
    "NUTS": transform_nuts_table
}


def generate_link_to_notice(notice_uri: str) -> Optional[str]:
    """
        Generates the link to the notice from the Notice URI
        :param notice_uri: URI of the lot as str
        :return: Link to the notice as str

        example Notice URI: epd:id_2015-S-250-456405_Notice
    """
    if not notice_uri:
        return None
    lot_id = re.search(r"id_(.*)_Notice", notice_uri)
    if lot_id is None:
        return None
    lot_id = lot_id.group(1)
    notice_year = lot_id.split('-')[0]
    notice_number = lot_id.split('-')[-1]
    return TED_NOTICES_LINK.format(notice_id=f"{notice_number}-{notice_year}")


class PostgresETLException(Exception):
    """
        Postgres ETL Exception
    """
    pass


class PostgresETLPipeline(ETLPipelineABC):
    """
        ETL Class that gets data from TDA endpoint, transforms and inserts result to document storage
    """

    def __init__(self, table_name: str, sparql_query_path: Path, postgres_url: str = None):
        """
            Constructor
        """
        self.etl_metadata = {}
        self.table_name = table_name
        self.sparql_query_path = sparql_query_path
        self.postgres_url = postgres_url if postgres_url else POSTGRES_URL
        self.sql_engine = sqlalchemy.create_engine(self.postgres_url, echo=False)

    def set_metadata(self, etl_metadata: dict):
        """
            Sets the metadata for the pipeline
            :param etl_metadata: Metadata for the pipeline
        """
        self.etl_metadata = etl_metadata

    def get_metadata(self) -> dict:
        """
            Returns the metadata for the pipeline
        """
        return self.etl_metadata

    def get_pipeline_name(self) -> str:
        """
            Returns the name of the pipeline
        """
        return self.table_name

    def extract(self) -> Dict:
        """
            Extracts data from triple store
        """
        sparql_query_str = self.sparql_query_path.read_text(encoding="utf-8")
        triple_store_endpoint = GraphDBAdapter().get_sparql_triple_store_endpoint(repository_name=TRIPLE_STORE_ENDPOINT)
        result_table = triple_store_endpoint.with_query(sparql_query_str).fetch_tabular()
        return {"data": result_table}

    def transform(self, extracted_data: Dict) -> Dict:
        """
            Transforms data from triple store
        """
        data_table: DataFrame = extracted_data["data"]
        if data_table.empty:
            raise PostgresETLException("No data was been fetched from triple store!")

        if self.table_name in TRANSFORMED_TABLES.keys():
            data_table = TRANSFORMED_TABLES[self.table_name](data_table)

        return {"data": data_table}

    def load(self, transformed_data: Dict):
        """
            Loads data to postgres
        """
        data_table: DataFrame = transformed_data["data"]

        with self.sql_engine.connect() as sql_connection:
            data_table.to_sql(self.table_name, con=sql_connection, if_exists='replace', chunksize=SEND_CHUNK_SIZE)

        return {"data": transformed_data["data"]}
