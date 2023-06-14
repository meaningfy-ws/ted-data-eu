import io
import logging
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from string import Template
from typing import Dict, Optional, List

import pandas as pd
import sqlalchemy
from pandas import DataFrame
from sqlalchemy.exc import IntegrityError
from ted_sws.data_manager.adapters.triple_store import TripleStoreABC

from ted_data_eu import config
from ted_data_eu.adapters.cpv_processor import CellarCPVProcessor
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC
from ted_data_eu.adapters.nuts_processor import CellarNUTSProcessor, NUTSProcessor
from ted_data_eu.adapters.triple_store import GraphDBAdapter, TDATripleStoreEndpoint
from ted_data_eu.services.currency_convertor import convert_currency
from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import START_DATE_METADATA_FIELD, \
    generate_sparql_filter_by_date_range, END_DATE_METADATA_FIELD

TED_NOTICES_LINK = 'https://ted.europa.eu/udl?uri=TED:NOTICE:{notice_id}:TEXT:EN:HTML'
TRIPLE_STORE_ENDPOINT = "notices"
POSTGRES_URL = f"postgresql://{config.POSTGRES_TDA_DB_USER}:{config.POSTGRES_TDA_DB_PASSWORD}@{config.POSTGRES_HOST}:{config.POSTGRES_TDA_DB_PORT}/{config.POSTGRES_TDA_DB_NAME}"
EURO_CURRENCY_ID = "EUR"
SEND_CHUNK_SIZE = 1000
DATA_FIELD = "data"
SQLALCHEMY_ISOLATION_LEVEL = "AUTOCOMMIT"
CELLAR_ENDPOINT_URL = "https://publications.europa.eu/webapi/rdf/sparql"
SKIP_NEXT_STEP_FIELD = "skip_step"
EURO_ENDING = "EUR"
MIN_CPV_LVL = 0
MAX_CPV_LVL = MIN_CPV_LVL + 5
MIN_NUTS_LVL = 0
MAX_NUTS_LVL = MIN_NUTS_LVL + 3
LIST_SEPARATOR = "|||"
ERROR_NO_DATA_FETCHED = "No data was been fetched from triple store!"

AMOUNT_VALUE_EUR_COLUMN = "AmountValueEUR"
AMOUNT_VALUE_COLUMN = "AmountValue"
CURRENCY_ID_COLUMN = "CurrencyId"
CONVERSION_TO_EUR_DATE_COLUMN = "ConversionToEURDate"

NOTICE_LINK_COLUMN = "NoticeLink"
NOTICE_ID_COLUMN = "NoticeId"
NOTICE_YEAR_COLUMN = "NoticeYear"
NOTICE_NUMBER_COLUMN = "NoticeNumber"
NOTICE_PUBLICATION_DATE_COLUMN = "NoticePublicationDate"

ORIGINAL_CPV_COLUMN = "OriginalCPV"
ORIGINAL_CPV_LABEL_COLUMN = "OriginalCPVLabel"
ORIGINAL_CPV_LEVEL_COLUMN = "OriginalCPVLevel"

NUTS_LABEL_COLUMN = "NUTSLabel"
NUTS_LEVEL_COLUMN = "NUTSLevel"
NUTS_ID_COLUMN = "NUTSId"
NUTS_LABEL_ENG_COLUMN = "NUTSLabelEng"

HIGHEST_RECEIVED_TENDER_VALUE_COLUMN = 'HighestReceivedTenderValue'
HIGHEST_RECEIVED_TENDER_VALUE_CURRENCY_COLUMN = 'HighestReceivedTenderValueCurrency'
LOWEST_RECEIVED_TENDER_VALUE_COLUMN = 'LowestReceivedTenderValue'
LOWEST_RECEIVED_TENDER_VALUE_CURRENCY_COLUMN = 'LowestReceivedTenderValueCurrency'

LOT_ESTIMATED_VALUE_COLUMN = "LotEstimatedValue"
LOT_ESTIMATED_VALUE_CURRENCY_COLUMN = "LotEstimatedValueCurrency"
TOTAL_AWARDED_VALUE_COLUMN = "TotalAwardedValue"
TOTAL_AWARDED_VALUE_CURRENCY_COLUMN = "TotalAwardedValueCurrency"
LOT_AWARDED_VALUE_COLUMN = "LotAwardedValue"
LOT_AWARDED_VALUE_CURRENCY_COLUMN = "LotAwardedValueCurrency"
LOT_BARGAIN_PRICE_COLUMN = "LotBargainPrice"
LOT_BARGAIN_PRICE_CURRENCY_COLUMN = "LotBargainPriceCurrency"
PROCEDURE_ESTIMATED_VALUE_COLUMN = "ProcedureEstimatedValue"
PROCEDURE_ESTIMATED_VALUE_CURRENCY_COLUMN = "ProcedureEstimatedValueCurrency"
LOT_SPECIFIC_CPV_COLUMN_NAME = "LotSpecificCPV"
WINNER_ID_COLUMN_NAME = "WinnerId"
PROCEDURE_CPV_COLUMN_NAME = "ProcedureCPV"
BUYER_ID_COLUMN_NAME = "BuyerId"

NUTS_LEVEL_TEMPLATE = "NUTS{nuts_lvl}"
NUTS_LABEL_TEMPLATE = "NUTS{nuts_lvl}Label"
NUTS_LABEL_ENG_TEMPLATE = "NUTS{nuts_lvl}LabelEng"
CPV_LEVEL_TEMPLATE = "CPV{cpv_lvl}"
CPV_LABEL_TEMPLATE = "CPV{cpv_lvl}Label"

DROP_DUPLICATES_QUERY = """
DELETE FROM "{table_name}" a USING (
    SELECT MIN(ctid) as ctid, "{primary_key_column_name}"
    FROM "{table_name}" 
    GROUP BY "{primary_key_column_name}" HAVING COUNT(*) > 1
) b
WHERE a."{primary_key_column_name}" = b."{primary_key_column_name}" 
AND a.ctid <> b.ctid
"""

ADD_PRIMARY_KEY_IF_NOT_EXISTS_QUERY = """DO $$ BEGIN IF NOT exists 
(select constraint_name from information_schema.table_constraints where 
table_name='{table_name}' and constraint_type = 'PRIMARY KEY') 
then ALTER TABLE "{table_name}" ADD PRIMARY KEY ("{primary_key_column_name}"); end if; END $$;
"""

ADD_FOREIGN_KEY_IF_NOT_EXISTS_QUERY = """DO $$ BEGIN IF NOT exists
(select constraint_name from information_schema.table_constraints where
table_name='{table_name}' and constraint_type = 'FOREIGN KEY')
then ALTER TABLE "{table_name}" ADD FOREIGN KEY ("{foreign_key_column_name}") REFERENCES "{foreign_key_table_name}" ("{foreign_key_column_name}");
end if; END $$;
"""

TABLE_EXISTS_QUERY = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE  table_schema = 'public'
        AND    table_name   = '{table_name}'
    );
"""

INSERT_QUERY = """
INSERT INTO "{table_name}" ({columns}) VALUES {values} ON CONFLICT DO NOTHING;
"""

DROP_TABLE_IF_EXISTS_QUERY = """
DROP TABLE IF EXISTS "{table_name}";
"""


def transform_notice_table(data_csv: io.StringIO) -> DataFrame:
    """
    Transforms notice table by adding link to notice and converting currency to EUR
    """
    data_table = pd.read_csv(data_csv, dtype={
        TOTAL_AWARDED_VALUE_COLUMN: float
    }, parse_dates=[NOTICE_PUBLICATION_DATE_COLUMN])
    data_table[NOTICE_LINK_COLUMN] = data_table.apply(
        lambda x: generate_link_to_notice(x[NOTICE_ID_COLUMN]), axis=1)

    # Convert currency to EUR
    data_table[TOTAL_AWARDED_VALUE_COLUMN] = data_table.apply(
        lambda x: convert_currency(amount=x[TOTAL_AWARDED_VALUE_COLUMN],
                                   currency=x[TOTAL_AWARDED_VALUE_CURRENCY_COLUMN],
                                   new_currency=EURO_CURRENCY_ID),
        axis=1)
    # change monetary value column type to int
    data_table[TOTAL_AWARDED_VALUE_COLUMN] = data_table[TOTAL_AWARDED_VALUE_COLUMN].astype(int)
    # Rename column to indicate that it is in EUR
    data_table.rename(columns={TOTAL_AWARDED_VALUE_COLUMN: f"{TOTAL_AWARDED_VALUE_COLUMN}{EURO_ENDING}"}, inplace=True)
    # Remove currency column
    data_table.drop(columns=[TOTAL_AWARDED_VALUE_CURRENCY_COLUMN], inplace=True)
    # Add notice year column
    data_table[NOTICE_YEAR_COLUMN] = data_table.apply(lambda x: generate_notice_year(x[NOTICE_ID_COLUMN]), axis=1)
    # Add notice Number column
    data_table[NOTICE_NUMBER_COLUMN] = data_table.apply(lambda x: generate_notice_number(x[NOTICE_ID_COLUMN]), axis=1)
    # Remove duplicates
    data_table.drop_duplicates(inplace=True)
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
    # change monetary value column type to int
    data_table[HIGHEST_RECEIVED_TENDER_VALUE_COLUMN] = data_table[HIGHEST_RECEIVED_TENDER_VALUE_COLUMN].astype(int)
    data_table[LOWEST_RECEIVED_TENDER_VALUE_COLUMN] = data_table[LOWEST_RECEIVED_TENDER_VALUE_COLUMN].astype(int)
    # rename columns to include currency name EUR
    data_table.rename(
        columns={HIGHEST_RECEIVED_TENDER_VALUE_COLUMN: f"{HIGHEST_RECEIVED_TENDER_VALUE_COLUMN}{EURO_ENDING}",
                 LOWEST_RECEIVED_TENDER_VALUE_COLUMN: f"{LOWEST_RECEIVED_TENDER_VALUE_COLUMN}{EURO_ENDING}"},
        inplace=True)
    # drop currency columns
    data_table.drop(
        columns=[HIGHEST_RECEIVED_TENDER_VALUE_CURRENCY_COLUMN, LOWEST_RECEIVED_TENDER_VALUE_CURRENCY_COLUMN],
        inplace=True)
    data_table.drop_duplicates(inplace=True)
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
    # change monetary value column type to int
    data_table[LOT_ESTIMATED_VALUE_COLUMN] = data_table[LOT_ESTIMATED_VALUE_COLUMN].astype(int)
    # rename columns to include currency name EUR
    data_table.rename(columns={LOT_ESTIMATED_VALUE_COLUMN: f"{LOT_ESTIMATED_VALUE_COLUMN}{EURO_ENDING}"},
                      inplace=True)
    # drop currency columns
    data_table.drop(
        columns=[LOT_ESTIMATED_VALUE_CURRENCY_COLUMN],
        inplace=True)

    data_table.drop_duplicates(inplace=True)

    return data_table


def transform_lot_cpv_table(data_csv: io.StringIO) -> DataFrame:
    """

    """
    data_table = pd.read_csv(data_csv, dtype=str)
    data_table.drop_duplicates(inplace=True)
    return data_table


def transform_procedure_cpv_table(data_csv: io.StringIO) -> DataFrame:
    """

    """
    data_table = pd.read_csv(data_csv, dtype=str)
    data_table.drop_duplicates(inplace=True)
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
    # change monetary value column type to int
    data_table[LOT_AWARDED_VALUE_COLUMN] = data_table[LOT_AWARDED_VALUE_COLUMN].astype(int)
    data_table[LOT_BARGAIN_PRICE_COLUMN] = data_table[LOT_BARGAIN_PRICE_COLUMN].astype(int)
    # rename columns to include currency name EUR
    data_table.rename(columns={LOT_AWARDED_VALUE_COLUMN: f"{LOT_AWARDED_VALUE_COLUMN}{EURO_ENDING}",
                               LOT_BARGAIN_PRICE_COLUMN: f"{LOT_BARGAIN_PRICE_COLUMN}{EURO_ENDING}"},
                      inplace=True)
    # drop currency columns
    data_table.drop(
        columns=[LOT_AWARDED_VALUE_CURRENCY_COLUMN, LOT_BARGAIN_PRICE_CURRENCY_COLUMN],
        inplace=True)
    data_table.drop_duplicates(inplace=True)

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
    # change monetary value column type to int
    data_table[PROCEDURE_ESTIMATED_VALUE_COLUMN] = data_table[PROCEDURE_ESTIMATED_VALUE_COLUMN].astype(int)
    # rename columns to include currency name EUR
    data_table.rename(columns={PROCEDURE_ESTIMATED_VALUE_COLUMN: f"{PROCEDURE_ESTIMATED_VALUE_COLUMN}{EURO_ENDING}"},
                      inplace=True)
    # drop currency columns
    data_table.drop(
        columns=[PROCEDURE_ESTIMATED_VALUE_CURRENCY_COLUMN],
        inplace=True)
    data_table.drop_duplicates(inplace=True)

    return data_table


def transform_cpv_table(data_csv: io.StringIO) -> DataFrame:
    """
    Transforms CPV table by adding all nuts levels with their labels
    """

    cpv_processor = CellarCPVProcessor(data_csv)

    data_table: DataFrame = cpv_processor.dataframe.copy(deep=True)
    data_table.rename(columns={cpv_processor.CPV_CODE_COLUMN: ORIGINAL_CPV_COLUMN,
                               cpv_processor.CPV_LABEL_COLUMN: ORIGINAL_CPV_LABEL_COLUMN}, inplace=True)
    data_table.drop(columns=[cpv_processor.CPV_PARENT_COLUMN], inplace=True)

    data_table[ORIGINAL_CPV_LEVEL_COLUMN] = data_table.apply(
        lambda row: cpv_processor.get_cpv_rank(row[ORIGINAL_CPV_COLUMN]), axis=1)
    for cpv_lvl in range(MIN_CPV_LVL, MAX_CPV_LVL + 1):
        data_table[CPV_LEVEL_TEMPLATE.format(cpv_lvl=cpv_lvl)] = data_table.apply(
            lambda row: cpv_processor.get_cpv_parent_code_by_rank(row[ORIGINAL_CPV_COLUMN], cpv_lvl), axis=1)
        data_table[CPV_LABEL_TEMPLATE.format(cpv_lvl=cpv_lvl)] = data_table.apply(
            lambda x: cpv_processor.get_cpv_label_by_code(x[CPV_LEVEL_TEMPLATE.format(cpv_lvl=cpv_lvl)]), axis=1)
    data_table.drop_duplicates(inplace=True)
    return data_table


def transform_nuts_table(data_csv: io.StringIO) -> DataFrame:
    """
    Transforms NUTS table by adding all nuts levels with their labels
    """
    cellar_nuts_processor = CellarNUTSProcessor(data_csv)
    static_nuts_processor = NUTSProcessor()
    data_table: DataFrame = cellar_nuts_processor.dataframe.copy(deep=True)
    data_table.rename(columns={cellar_nuts_processor.NUTS_CODE_COLUMN_NAME: NUTS_ID_COLUMN,
                               cellar_nuts_processor.NUTS_LABEL_COLUMN_NAME: NUTS_LABEL_COLUMN}, inplace=True)
    data_table.drop(columns=[cellar_nuts_processor.NUTS_PARENT_COLUMN_NAME], inplace=True)

    data_table[NUTS_LABEL_ENG_COLUMN] = data_table.apply(
        lambda x: static_nuts_processor.get_nuts_label_by_code(x[NUTS_ID_COLUMN]),
        axis=1)
    for nuts_lvl in range(MIN_NUTS_LVL, MAX_NUTS_LVL + 1):
        data_table[NUTS_LEVEL_TEMPLATE.format(nuts_lvl=nuts_lvl)] = data_table.apply(
            lambda x: cellar_nuts_processor.get_nuts_parent_code_by_level(x[NUTS_ID_COLUMN], nuts_lvl), axis=1)
        data_table[NUTS_LABEL_TEMPLATE.format(nuts_lvl=nuts_lvl)] = data_table.apply(
            lambda x: cellar_nuts_processor.get_nuts_label_by_code(x[NUTS_LEVEL_TEMPLATE.format(nuts_lvl=nuts_lvl)]),
            axis=1)
        data_table[NUTS_LABEL_ENG_TEMPLATE.format(nuts_lvl=nuts_lvl)] = data_table.apply(
            lambda x: static_nuts_processor.get_nuts_label_by_code(x[NUTS_LEVEL_TEMPLATE.format(nuts_lvl=nuts_lvl)]),
            axis=1)
    data_table.drop_duplicates(inplace=True)
    return data_table


TRANSFORMED_TABLES = {
    "Notice": transform_notice_table,
    "SubmissionStatisticalInformation": transform_statistical_information_table,
    "Lot": transform_lot_table,
    "LotAwardOutcome": transform_lot_award_outcome_table,
    "Procedure": transform_procedure_table,
    "CPV": transform_cpv_table,
    "NUTS": transform_nuts_table,
    "LotCPV": transform_lot_cpv_table,
    "ProcedureCPV": transform_procedure_cpv_table,
}


def get_notice_metadata(notice_uri: str) -> Optional[Dict]:
    """
        Gets the metadata of the notice from the Notice URI
        :param notice_uri: URI of the lot as str
        :return: Metadata of the notice as dict

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
    return {
        NOTICE_YEAR_COLUMN: notice_year,
        NOTICE_NUMBER_COLUMN: notice_number
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
    notice_metadata = get_notice_metadata(notice_uri)
    if notice_metadata is None:
        return None
    return TED_NOTICES_LINK.format(
        notice_id=f"{notice_metadata[NOTICE_NUMBER_COLUMN]}-{notice_metadata[NOTICE_YEAR_COLUMN]}")


def generate_notice_year(notice_uri: str) -> Optional[str]:
    """
        Generates the year of the notice from the Notice URI
        :param notice_uri: URI of the lot as str
        :return: Year of the notice as str

        example Notice URI: epd:id_2015-S-250-456405_Notice
    """
    if not notice_uri:
        return None
    notice_metadata = get_notice_metadata(notice_uri)
    if notice_metadata is None:
        return None
    return notice_metadata[NOTICE_YEAR_COLUMN]


def generate_notice_number(notice_uri: str) -> Optional[str]:
    """
        Generates the number of the notice from the Notice URI
        :param notice_uri: URI of the lot as str
        :return: Number of the notice as str

        example Notice URI: epd:id_2015-S-250-456405_Notice
    """
    if not notice_uri:
        return None
    notice_metadata = get_notice_metadata(notice_uri)
    if notice_metadata is None:
        return None
    return notice_metadata[NOTICE_NUMBER_COLUMN]


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
                 postgres_url: str = None, foreign_key_column_names: List[dict] = None,
                 triple_store: TripleStoreABC = None, triple_store_endpoint: str = None):
        """
            Constructor
        """
        self.etl_metadata = {}
        self.table_name = table_name
        self.sparql_query_path = sparql_query_path
        self.postgres_url = postgres_url if postgres_url else POSTGRES_URL
        self.sql_engine = sqlalchemy.create_engine(self.postgres_url, echo=False,
                                                   isolation_level=SQLALCHEMY_ISOLATION_LEVEL)
        self.primary_key_column_name = primary_key_column_name
        self.foreign_key_column_names = foreign_key_column_names if foreign_key_column_names else []
        self.triple_store = triple_store or GraphDBAdapter()
        self.triple_store_endpoint = triple_store_endpoint or TRIPLE_STORE_ENDPOINT

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
        triple_store_endpoint = self.triple_store.get_sparql_tda_triple_store_endpoint(
            repository_name=self.triple_store_endpoint)
        result_table = triple_store_endpoint.with_query(sparql_query).fetch_csv()
        return {DATA_FIELD: result_table}

    def transform(self, extracted_data: Dict) -> Dict:
        """
            Transforms data from triple store
        """
        skip_transform = extracted_data.get(SKIP_NEXT_STEP_FIELD, False)
        if skip_transform:
            return extracted_data
        data_json: io.StringIO = extracted_data.get(DATA_FIELD, None)
        if not data_json:
            raise PostgresETLException(ERROR_NO_DATA_FETCHED)
        extracted_table: DataFrame = pd.read_csv(data_json)
        if extracted_table.empty:
            raise PostgresETLException(ERROR_NO_DATA_FETCHED)
        data_json.seek(0)
        if self.table_name in TRANSFORMED_TABLES.keys():
            data_table: DataFrame = TRANSFORMED_TABLES[self.table_name](data_json)
        else:
            data_table: DataFrame = pd.read_csv(data_json)
        extracted_data[DATA_FIELD] = data_table
        return extracted_data

    def load(self, transformed_data: Dict):
        """
            Loads data to postgres
        """
        skip_load = transformed_data.get(SKIP_NEXT_STEP_FIELD, False)
        if skip_load:
            return transformed_data
        data_table: DataFrame = transformed_data[DATA_FIELD]

        with self.sql_engine.connect() as sql_connection:
            try:
                data_table.to_sql(self.table_name, con=sql_connection, if_exists='append',
                                  chunksize=SEND_CHUNK_SIZE,
                                  index=False)
            except IntegrityError:
                logging.error("Duplicate primary key found")
                logging.error("Table name: %s", self.table_name)
                logging.error("Date: START: %s END: %s", self.etl_metadata[START_DATE_METADATA_FIELD],
                              self.etl_metadata[END_DATE_METADATA_FIELD])
                logging.error("Primary key column name: %s", self.primary_key_column_name)
                logging.error("Foreign key column names: %s", self.foreign_key_column_names)
                logging.error("Data: %s", data_table.to_string())
                raise PostgresETLException()

            sql_connection.execute(DROP_DUPLICATES_QUERY.format(table_name=self.table_name,
                                                                primary_key_column_name=self.primary_key_column_name))

            sql_connection.execute(ADD_PRIMARY_KEY_IF_NOT_EXISTS_QUERY.format(table_name=self.table_name,
                                                                              primary_key_column_name=self.primary_key_column_name))
            # TODO: Temporary disabled because ETL works in parallel and foreign keys are not created in time
            # also see issue: https://github.com/pandas-dev/pandas/issues/15988
            # for foreign_keys in self.foreign_key_column_names:
            #     for foreign_key_column_name, foreign_key_table_name in foreign_keys.items():
            #         fk_table_exists = sql_connection.execute(
            #             TABLE_EXISTS_QUERY.format(table_name=foreign_key_table_name)).fetchone()[0]
            #         if fk_table_exists:
            #             sql_connection.execute(ADD_FOREIGN_KEY_IF_NOT_EXISTS_QUERY.format(table_name=self.table_name,
            #                                                                               foreign_key_column_name=foreign_key_column_name,
            #                                                                               foreign_key_table_name=foreign_key_table_name))

        return {DATA_FIELD: transformed_data[DATA_FIELD]}


class CellarETLPipeline(PostgresETLPipeline):
    def extract(self) -> Dict:
        """
            Extracts data from cellar
        """
        with self.sql_engine.connect() as sql_connection:
            table_exists = sql_connection.execute(TABLE_EXISTS_QUERY.format(table_name=self.table_name)).fetchone()[0]
            if table_exists:
                return {DATA_FIELD: None, SKIP_NEXT_STEP_FIELD: True}

        cellar_endpoint = TDATripleStoreEndpoint(CELLAR_ENDPOINT_URL)
        data_table = cellar_endpoint.with_query(
            self.sparql_query_path.read_text(encoding='utf-8')).fetch_csv()

        return {DATA_FIELD: data_table, SKIP_NEXT_STEP_FIELD: False}
