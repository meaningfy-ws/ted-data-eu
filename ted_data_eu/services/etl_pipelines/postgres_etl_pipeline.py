import io
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
from ted_data_eu.services.currency_convertor import convert_currency
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

HIGHEST_RECEIVED_TENDER_VALUE_COLUMN = 'HighestReceivedTenderValue'
HIGHEST_RECEIVED_TENDER_VALUE_CURRENCY_COLUMN = 'HighestReceivedTenderValueCurrency'
LOWEST_RECEIVED_TENDER_VALUE_COLUMN = 'LowestReceivedTenderValue'
LOWEST_RECEIVED_TENDER_VALUE_CURRENCY_COLUMN = 'LowestReceivedTenderValueCurrency'

LOT_ESTIMATED_VALUE_COLUMN = "LotEstimatedValue"
LOT_ESTIMATED_VALUE_CURRENCY_COLUMN = "LotEstimatedValueCurrency"
LOT_RESTATED_ESTIMATED_VALUE_COLUMN = "LotRestatedEstimatedValue"
LOT_RESTATED_ESTIMATED_VALUE_CURRENCY_COLUMN = "LotRestatedEstimatedValueCurrency"
TOTAL_AWARDED_VALUE_COLUMN = "TotalAwardedValue"
TOTAL_AWARDED_VALUE_CURRENCY_COLUMN = "TotalAwardedValueCurrency"
LOT_AWARDED_VALUE_COLUMN = "LotAwardedValue"
LOT_AWARDED_VALUE_CURRENCY_COLUMN = "LotAwardedValueCurrency"
LOT_BARGAIN_PRICE_COLUMN = "LotBargainPrice"
LOT_BARGAIN_PRICE_CURRENCY_COLUMN = "LotBargainPriceCurrency"
PROCEDURE_ESTIMATED_VALUE_COLUMN = "ProcedureEstimatedValue"
PROCEDURE_ESTIMATED_VALUE_CURRENCY_COLUMN = "ProcedureEstimatedValueCurrency"

DROP_DUPLICATES_QUERY = """
DELETE FROM "{table_name}" a USING (
    SELECT MIN(ctid) as ctid, "{primary_key_column_name}"
    FROM "{table_name}" 
    GROUP BY "{primary_key_column_name}" HAVING COUNT(*) > 1
) b
WHERE a."{primary_key_column_name}" = b."{primary_key_column_name}" 
AND a.ctid <> b.ctid
"""


def transform_notice_table(data_csv: io.StringIO) -> DataFrame:
    """
    Transforms notice table by adding link to notice and converting currency to EUR
    """
    data_table = pd.read_csv(data_csv, dtype=object)
    data_table[NOTICE_LINK_COLUMN] = data_table.apply(
        lambda x: generate_link_to_notice(x[NOTICE_ID_COLUMN]), axis=1)

    # Convert currency to EUR
    data_table[TOTAL_AWARDED_VALUE_COLUMN] = data_table.apply(
        lambda x: convert_currency(amount=x[TOTAL_AWARDED_VALUE_COLUMN],
                                   currency=x[TOTAL_AWARDED_VALUE_CURRENCY_COLUMN],
                                   new_currency=EURO_CURRENCY_ID),
        axis=1)
    # Rename column to indicate that it is in EUR
    data_table.rename(columns={TOTAL_AWARDED_VALUE_COLUMN: f"{TOTAL_AWARDED_VALUE_COLUMN}EUR"}, inplace=True)
    # Remove currency column
    data_table.drop(columns=[TOTAL_AWARDED_VALUE_CURRENCY_COLUMN], inplace=True)
    return data_table


def transform_purpose_table(data_csv: io.StringIO) -> DataFrame:
    """
    Transforms purpose table by adding CPV codes and labels on all levels
    """
    cpv_processor = CPVProcessor()
    data_table = pd.read_csv(data_csv, dtype={ORIGINAL_CPV_COLUMN: str})
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


def transform_nuts_table(data_csv: io.StringIO) -> DataFrame:
    """
    Transforms nuts table by adding NUTS codes and labels on all levels
    """
    data_table = pd.read_csv(data_csv)
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


def transform_statistical_information_table(data_csv: io.StringIO) -> DataFrame:
    """
    Transforms statistical information table by adding monetary values in EUR
    """
    data_table = pd.read_csv(data_csv)
    # convert monetary value to EUR
    data_table[HIGHEST_RECEIVED_TENDER_VALUE_COLUMN] = data_table.apply(
        lambda x: convert_currency(amount=x[HIGHEST_RECEIVED_TENDER_VALUE_COLUMN],
                                   currency=x[HIGHEST_RECEIVED_TENDER_VALUE_CURRENCY_COLUMN],
                                   new_currency=EURO_CURRENCY_ID),
        axis=1)
    data_table[LOWEST_RECEIVED_TENDER_VALUE_COLUMN] = data_table.apply(
        lambda x: convert_currency(amount=x[LOWEST_RECEIVED_TENDER_VALUE_COLUMN],
                                   currency=x[LOWEST_RECEIVED_TENDER_VALUE_CURRENCY_COLUMN],
                                   new_currency=EURO_CURRENCY_ID),
        axis=1)
    # rename columns to include currency name EUR
    data_table.rename(columns={HIGHEST_RECEIVED_TENDER_VALUE_COLUMN: f"{HIGHEST_RECEIVED_TENDER_VALUE_COLUMN}EUR",
                               LOWEST_RECEIVED_TENDER_VALUE_COLUMN: f"{LOWEST_RECEIVED_TENDER_VALUE_COLUMN}EUR"},
                      inplace=True)
    # drop currency columns
    data_table.drop(
        columns=[HIGHEST_RECEIVED_TENDER_VALUE_CURRENCY_COLUMN, LOWEST_RECEIVED_TENDER_VALUE_CURRENCY_COLUMN],
        inplace=True)

    return data_table


def transform_lot_table(data_csv: io.StringIO) -> DataFrame:
    """
    Transforms lot table by adding monetary values in EUR
    """
    data_table = pd.read_csv(data_csv)
    # convert monetary value to EUR
    data_table[LOT_ESTIMATED_VALUE_COLUMN] = data_table.apply(
        lambda x: convert_currency(amount=x[LOT_ESTIMATED_VALUE_COLUMN],
                                   currency=x[LOT_ESTIMATED_VALUE_CURRENCY_COLUMN],
                                   new_currency=EURO_CURRENCY_ID),
        axis=1)
    data_table[LOT_RESTATED_ESTIMATED_VALUE_COLUMN] = data_table.apply(
        lambda x: convert_currency(amount=x[LOT_RESTATED_ESTIMATED_VALUE_COLUMN],
                                   currency=x[LOT_RESTATED_ESTIMATED_VALUE_CURRENCY_COLUMN],
                                   new_currency=EURO_CURRENCY_ID),
        axis=1)
    # rename columns to include currency name EUR
    data_table.rename(columns={LOT_ESTIMATED_VALUE_COLUMN: f"{LOT_ESTIMATED_VALUE_COLUMN}EUR",
                               LOT_RESTATED_ESTIMATED_VALUE_COLUMN: f"{LOT_RESTATED_ESTIMATED_VALUE_COLUMN}EUR"},
                      inplace=True)
    # drop currency columns
    data_table.drop(
        columns=[LOT_ESTIMATED_VALUE_CURRENCY_COLUMN, LOT_RESTATED_ESTIMATED_VALUE_CURRENCY_COLUMN],
        inplace=True)

    return data_table


def transform_lot_award_outcome_table(data_csv: io.StringIO) -> DataFrame:
    """
    Transforms LotAwardOutcome table by adding monetary values in EUR
    """
    data_table = pd.read_csv(data_csv)
    # convert monetary value to EUR
    data_table[LOT_AWARDED_VALUE_COLUMN] = data_table.apply(
        lambda x: convert_currency(amount=x[LOT_AWARDED_VALUE_COLUMN],
                                   currency=x[LOT_AWARDED_VALUE_CURRENCY_COLUMN],
                                   new_currency=EURO_CURRENCY_ID),
        axis=1)
    data_table[LOT_BARGAIN_PRICE_COLUMN] = data_table.apply(
        lambda x: convert_currency(amount=x[LOT_BARGAIN_PRICE_COLUMN],
                                   currency=x[LOT_BARGAIN_PRICE_CURRENCY_COLUMN],
                                   new_currency=EURO_CURRENCY_ID),
        axis=1)
    # rename columns to include currency name EUR
    data_table.rename(columns={LOT_AWARDED_VALUE_COLUMN: f"{LOT_AWARDED_VALUE_COLUMN}EUR",
                               LOT_BARGAIN_PRICE_COLUMN: f"{LOT_BARGAIN_PRICE_COLUMN}EUR"},
                      inplace=True)
    # drop currency columns
    data_table.drop(
        columns=[LOT_AWARDED_VALUE_CURRENCY_COLUMN, LOT_BARGAIN_PRICE_CURRENCY_COLUMN],
        inplace=True)

    return data_table


def transform_procedure_table(data_csv: io.StringIO) -> DataFrame:
    """
    Transforms Procedure table by adding monetary values in EUR
    """
    data_table = pd.read_csv(data_csv)
    # convert monetary value to EUR
    data_table[PROCEDURE_ESTIMATED_VALUE_COLUMN] = data_table.apply(
        lambda x: convert_currency(amount=x[PROCEDURE_ESTIMATED_VALUE_COLUMN],
                                   currency=x[PROCEDURE_ESTIMATED_VALUE_CURRENCY_COLUMN],
                                   new_currency=EURO_CURRENCY_ID),
        axis=1)
    # rename columns to include currency name EUR
    data_table.rename(columns={PROCEDURE_ESTIMATED_VALUE_COLUMN: f"{PROCEDURE_ESTIMATED_VALUE_COLUMN}EUR"},
                      inplace=True)
    # drop currency columns
    data_table.drop(
        columns=[PROCEDURE_ESTIMATED_VALUE_CURRENCY_COLUMN],
        inplace=True)

    return data_table


TRANSFORMED_TABLES = {
    "Notice": transform_notice_table,
    "Purpose": transform_purpose_table,
    "NUTS": transform_nuts_table,
    "SubmissionStatisticalInformation": transform_statistical_information_table,
    "Lot": transform_lot_table,
    "LotAwardOutcome": transform_lot_award_outcome_table,
    "Procedure": transform_procedure_table
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

    def __init__(self, table_name: str, sparql_query_path: Path, primary_key_column_name: str,
                 postgres_url: str = None):
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
        triple_store_endpoint = GraphDBAdapter().get_sparql_tda_triple_store_endpoint(
            repository_name=TRIPLE_STORE_ENDPOINT)

        print("||||||||||||||||||||||||||||||||||||||||||")
        # print(triple_store_endpoint.endpoint)
        print(sparql_query)
        print("||||||||||||||||||||||||||||||||||||||||||")

        result_table = triple_store_endpoint.with_query(sparql_query).fetch_csv()
        return {"data": result_table}

    def transform(self, extracted_data: Dict) -> Dict:
        """
            Transforms data from triple store
        """
        data_json: io.StringIO = extracted_data["data"]
        if not data_json:
            raise PostgresETLException("No data was been fetched from triple store!")

        if self.table_name in TRANSFORMED_TABLES.keys():
            data_table: DataFrame = TRANSFORMED_TABLES[self.table_name](data_json)
        else:
            data_table: DataFrame = pd.read_csv(data_json)

        return {"data": data_table}

    def load(self, transformed_data: Dict):
        """
            Loads data to postgres
        """
        data_table: DataFrame = transformed_data["data"]

        with self.sql_engine.connect() as sql_connection:
            data_table.to_sql(self.table_name, con=sql_connection, if_exists='append', chunksize=SEND_CHUNK_SIZE,
                              index=False)
            sql_connection.execute(DROP_DUPLICATES_QUERY.format(table_name=self.table_name,
                                                                primary_key_column_name=self.primary_key_column_name))

        return {"data": transformed_data["data"]}


ADD_PRIMARY_KEY_IF_NOT_EXISTS_QUERY = """DO $$ BEGIN IF NOT exists 
(select constraint_name from information_schema.table_constraints where 
table_name='{table_name}' and constraint_type = 'PRIMARY KEY') 
then ALTER TABLE "{table_name}" ADD PRIMARY KEY ("{primary_key_column_name}"); end if; END $$;
"""

ADD_FOREIGN_KEY_IF_NOT_EXISTS_QUERY = """DO $$ BEGIN IF NOT exists
(select constraint_name from information_schema.table_constraints where
table_name='{table_name}' and constraint_type = 'FOREIGN KEY')
then ALTER TABLE "{table_name}" ADD FOREIGN KEY ("{foreign_key_column_name}") REFERENCES "{foreign_table_name}" ("{foreign_key_column_name}");
end if; END $$;
"""

if __name__ == "__main__":
    pd.options.display.float_format = "{:,.2f}".format

    etl = PostgresETLPipeline(table_name="Notice",
                              sparql_query_path=config.TABLE_QUERY_PATHS["Notice"],
                              primary_key_column_name="NoticeId")
    etl.set_metadata({"start_date": "20220907", "end_date": "20220907"})
    df: dict = etl.extract()['data']

    df: DataFrame = etl.transform({"data": df})['data']
    print(df.info())
    print(df.to_string())
    # etl.load({"data": df})

    # sql_engine = sqlalchemy.create_engine(POSTGRES_URL, echo=False, isolation_level="AUTOCOMMIT")
    # with sql_engine.connect() as sql_connection:
    #     q = ADD_FOREIGN_KEY_IF_NOT_EXISTS_QUERY.format(table_name="Tender", foreign_key_column_name="PurposeId", foreign_table_name="Purpose")
    #     print(q)
    #     #sql_connection.execution_options(autocommit=True)
    #     sql_connection.execute(q)
    #     #sql_connection.connection.commit()
