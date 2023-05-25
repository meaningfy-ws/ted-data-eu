import logging
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from string import Template
from typing import Dict, Optional

import pandas as pd
import sqlalchemy
from pandas import DataFrame

from ted_data_eu import config
from ted_data_eu.adapters.cpv_processor import CPVProcessor, CPV_MAX_RANK, CPV_MIN_RANK
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC
from ted_data_eu.adapters.nuts_processor import NUTSProcessor, NUTS_MIN_RANK, NUTS_MAX_RANK
from ted_data_eu.adapters.triple_store import GraphDBAdapter
from ted_data_eu.services.currency_convertor import convert_currency, \
    get_last_available_date_for_currency
from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import START_DATE_METADATA_FIELD, \
    generate_sparql_filter_by_date_range, END_DATE_METADATA_FIELD

TED_NOTICES_LINK = 'https://ted.europa.eu/udl?uri=TED:NOTICE:{notice_id}:TEXT:EN:HTML'
TRIPLE_STORE_ENDPOINT = "notices"
POSTGRES_URL = f"postgresql://{config.POSTGRES_TDA_DB_USER}:{config.POSTGRES_TDA_DB_PASSWORD}@{config.POSTGRES_HOST}:{config.POSTGRES_TDA_DB_PORT}/{config.POSTGRES_TDA_DB_NAME}"
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

DROP_DUPLICATES_QUERY = """
DELETE FROM "{table_name}" a USING (
    SELECT MIN(ctid) as ctid, "{primary_key_column_name}"
    FROM "{table_name}" 
    GROUP BY "{primary_key_column_name}" HAVING COUNT(*) > 1
) b
WHERE a."{primary_key_column_name}" = b."{primary_key_column_name}" 
AND a.ctid <> b.ctid
"""



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
    data_table[ORIGINAL_CPV_COLUMN] = data_table[ORIGINAL_CPV_COLUMN].astype(str)
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

    def __init__(self, table_name: str, sparql_query_path: Path, primary_key_column_name: str, postgres_url: str = None):
        """
            Constructor
        """
        self.etl_metadata = {}
        self.table_name = table_name
        self.sparql_query_path = sparql_query_path
        self.postgres_url = postgres_url if postgres_url else POSTGRES_URL
        self.sql_engine = sqlalchemy.create_engine(self.postgres_url, echo=False)
        self.primary_key_column_name = primary_key_column_name

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


        sparql_query_template = Template(self.sparql_query_path.read_text(encoding="utf-8"))
        sparql_query = sparql_query_template.substitute(date_range=date_range)
        triple_store_endpoint = GraphDBAdapter().get_sparql_triple_store_endpoint(repository_name=TRIPLE_STORE_ENDPOINT)
        result_table = triple_store_endpoint.with_query(sparql_query).fetch_tabular()
        return {"data": result_table}

    def transform(self, extracted_data: Dict) -> Dict:
        """
            Transforms data from triple store
        """
        data_table: DataFrame = extracted_data["data"]
        if data_table.empty:
            raise PostgresETLException("No data was been fetched from triple store!")
        data_table = data_table.astype(object)
        if self.table_name in TRANSFORMED_TABLES.keys():
            data_table = TRANSFORMED_TABLES[self.table_name](data_table)

        return {"data": data_table}

    def load(self, transformed_data: Dict):
        """
            Loads data to postgres
        """
        data_table: DataFrame = transformed_data["data"]

        with self.sql_engine.connect() as sql_connection:
            data_table.to_sql(self.table_name, con=sql_connection, if_exists='append', chunksize=SEND_CHUNK_SIZE, index=False)
            sql_connection.execute(DROP_DUPLICATES_QUERY.format(table_name=self.table_name, primary_key_column_name=self.primary_key_column_name))

        return {"data": transformed_data["data"]}
