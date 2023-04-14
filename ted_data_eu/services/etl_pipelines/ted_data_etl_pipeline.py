import logging
from datetime import datetime, date, timedelta
from string import Template
from typing import Dict
import re
import pandas as pd
from dateutil import rrule
from pandas import DataFrame
import numpy as np
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
TED_NOTICES_LINK = 'https://ted.europa.eu/udl?uri=TED:NOTICE:{notice_id}:TEXT:EN:HTML'

PROCEDURE_TYPE_COLUMN_NAME = "procedure_type"
WINNER_NUTS_COLUMN_NAME = "winner_nuts"
LOT_NUTS_COLUMN_NAME = "place_of_performance"
CURRENCY_COLUMN_NAME = "lot_currency"
PUBLICATION_DATE_COLUMN_NAME = "publication_date"
WINNER_NAME_COLUMN_NAME = "winner_names"
AMOUNT_VALUE_COLUMN_NAME = "lot_amount"
PROCEDURE_TITLE_COLUMN_NAME = "procedure_title"
LOT_URL_COLUMN_NAME = 'lot'
BUYER_NAME_COLUMN_NAME = 'buyer_names'
LOT_CPV_COLUMN_NAME = 'main_cpvs'
LOT_SUBCONTRACTING_COLUMN_NAME = 'subcontracting'
CONTRACT_DURATION_COLUMN_NAME = 'contract_duration'
AWARDED_CPB_COLUMN_NAME = 'awarded_cpb'
EA_TECHNIQUE_COLUMN_NAME = 'ea_technique'
FA_TECHNIQUE_COLUMN_NAME = 'fa_technique'
IS_GPA_COLUMN_NAME = 'is_gpa'
USING_EU_FUNDS_COLUMN_NAME = 'using_eu_funds'

AMOUNT_VALUE_EUR_COLUMN_NAME = 'amount_value_eur'
NOTICE_LINK = 'notice_link'

SUBCONTRACT_AVAILABLE_INDICATOR = 'indicator_transparency_subcontract_info_available'
DURATION_AVAILABLE_INDICATOR = 'indicator_transparency_duration_available'
JOINT_PROCUREMENT_INDICATOR = 'indicator_administrative_joint_procurement'
USE_OF_FRAMEWORK_AGREEMENT_INDICATOR = 'indicator_administrative_use_of_framework_agreement'
ELECTRONIC_AUCTION_INDICATOR = 'indicator_administrative_electronic_auction'
USE_OF_WTO_INDICATOR = 'indicator_administrative_use_of_wto'
IMPLEMENTATION_LOCATION_AVAILABLE_INDICATOR = 'indicator_transparency_implementation_location_available'
FUNDINGS_INFO_AVAILABLE_INDICATOR = 'indicator_transparency_funding_info_available'
PRODUCT_CODES_AVAILABLE_INDICATOR = 'indicator_transparency_product_codes_available'
BIDDER_NAME_AVAILABLE_INDICATOR = 'indicator_transparency_bidder_name_available'
CONTRACT_VALUE_AVAILABLE_INDICATOR = 'indicator_transparency_contract_value_available'
PROCEDURE_TYPE_INDICATOR = 'indicator_integrity_procedure_type'

CPV_RANK_1 = 'cpv1'
CPV_RANK_2 = 'cpv2'
CPV_RANK_3 = 'cpv3'
CPV_RANK_4 = 'cpv4'
CPV_RANK_5 = 'cpv5'
CPV_LEVELS = 'cpv_levels'
CPV_PARENT = 'cpv_parent'


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

        # delete rows with all empty columns
        data_table.dropna(how='all', inplace=True)
        data_table = data_table.replace({np.nan: None})

        if data_table.empty:
            raise TedETLException("No data was been fetched from triple store!")
        else:
            logging.info(data_table.head())

        # set columns types
        # data_table = data_table.astype({
        #     PROCEDURE_TYPE_COLUMN_NAME: str,
        #     WINNER_NUTS_COLUMN_NAME: str,
        #     LOT_NUTS_COLUMN_NAME: str,
        #     CURRENCY_COLUMN_NAME: str,
        #     # PUBLICATION_DATE_COLUMN_NAME: str,
        #     WINNER_NAME_COLUMN_NAME: str,
        #     # AMOUNT_VALUE_COLUMN_NAME: str,
        #     PROCEDURE_TITLE_COLUMN_NAME: str,
        #     LOT_URL_COLUMN_NAME: str,
        #     BUYER_NAME_COLUMN_NAME: str,
        #     LOT_CPV_COLUMN_NAME: str,
        #     #LOT_SUBCONTRACTING_COLUMN_NAME: str,
        #     CONTRACT_DURATION_COLUMN_NAME: str,
        #     AWARDED_CPB_COLUMN_NAME: str,
        #     EA_TECHNIQUE_COLUMN_NAME: str,
        #     FA_TECHNIQUE_COLUMN_NAME: str,
        #     # IS_GPA_COLUMN_NAME: str,
        #     # USING_EU_FUNDS_COLUMN_NAME: str,
        # })

        # data transform
        data_table[WINNER_NUTS_COLUMN_NAME] = data_table[WINNER_NUTS_COLUMN_NAME].apply(
            lambda x: x.split('/')[-1] if x else x)
        data_table[PROCEDURE_TYPE_COLUMN_NAME] = data_table[PROCEDURE_TYPE_COLUMN_NAME].apply(
            lambda x: x.split('/')[-1] if x else x)
        data_table[LOT_NUTS_COLUMN_NAME] = data_table[LOT_NUTS_COLUMN_NAME].apply(
            lambda x: x.split('/')[-1] if x else x)
        data_table[CURRENCY_COLUMN_NAME] = data_table[CURRENCY_COLUMN_NAME].apply(
            lambda x: x.split('/')[-1] if x else x)
        data_table[WINNER_NAME_COLUMN_NAME] = data_table[WINNER_NAME_COLUMN_NAME].apply(
            lambda x: x.split(' ||| ') if x else x)
        data_table[BUYER_NAME_COLUMN_NAME] = data_table[BUYER_NAME_COLUMN_NAME].apply(
            lambda x: x.split(' ||| ') if x else x)
        data_table[LOT_CPV_COLUMN_NAME] = data_table[LOT_CPV_COLUMN_NAME].apply(
            lambda x: [cpv.split('/')[-1] for cpv in x.split(' ||| ')] if x else x)
        data_table[PROCEDURE_TITLE_COLUMN_NAME] = data_table[PROCEDURE_TITLE_COLUMN_NAME].apply(
            lambda x: x.strip() if x else x)
        data_table[PUBLICATION_DATE_COLUMN_NAME] = data_table[PUBLICATION_DATE_COLUMN_NAME].apply(
            lambda x: pd.to_datetime(str(x), format='%Y%m%d') if x else x)

        # add new columns
        data_table[AMOUNT_VALUE_EUR_COLUMN_NAME] = data_table.apply(
            lambda x: x[AMOUNT_VALUE_COLUMN_NAME] if x[CURRENCY_COLUMN_NAME] == 'EUR' else convert_currency(
                amount=x[AMOUNT_VALUE_COLUMN_NAME],
                currency=x[CURRENCY_COLUMN_NAME],
                new_currency='EUR',
                date=x[PUBLICATION_DATE_COLUMN_NAME].date()
            ), axis=1)

        def generate_notice_link(lot_url):
            lot_id = re.search(r"id_(.*)_Lot_", lot_url).group(1)
            notice_year = lot_id.split('-')[0]
            notice_number = lot_id.split('-')[-1]
            return TED_NOTICES_LINK.format(notice_id=f"{notice_number}-{notice_year}")

        data_table[NOTICE_LINK] = data_table.apply(
            lambda x: generate_notice_link(x[LOT_URL_COLUMN_NAME]),
            axis=1)

        # rename columns with indicator
        data_table.rename(columns={
            LOT_SUBCONTRACTING_COLUMN_NAME: SUBCONTRACT_AVAILABLE_INDICATOR,
            CONTRACT_DURATION_COLUMN_NAME: DURATION_AVAILABLE_INDICATOR,
            AWARDED_CPB_COLUMN_NAME: JOINT_PROCUREMENT_INDICATOR,
            FA_TECHNIQUE_COLUMN_NAME: USE_OF_FRAMEWORK_AGREEMENT_INDICATOR,
            EA_TECHNIQUE_COLUMN_NAME: ELECTRONIC_AUCTION_INDICATOR,
            IS_GPA_COLUMN_NAME: USE_OF_WTO_INDICATOR,
            USING_EU_FUNDS_COLUMN_NAME: FUNDINGS_INFO_AVAILABLE_INDICATOR,
        }, inplace=True)

        # calculate renamed columns to indicators
        data_table[SUBCONTRACT_AVAILABLE_INDICATOR] = data_table[SUBCONTRACT_AVAILABLE_INDICATOR].apply(
            lambda x: 100 if x else 0)
        data_table[DURATION_AVAILABLE_INDICATOR] = data_table[DURATION_AVAILABLE_INDICATOR].apply(
            lambda x: 100 if x else 0)
        data_table[JOINT_PROCUREMENT_INDICATOR] = data_table[JOINT_PROCUREMENT_INDICATOR].apply(
            lambda x: 100 if x else 0)
        data_table[USE_OF_FRAMEWORK_AGREEMENT_INDICATOR] = data_table[USE_OF_FRAMEWORK_AGREEMENT_INDICATOR].apply(
            lambda x: 100 if x else 0)
        data_table[ELECTRONIC_AUCTION_INDICATOR] = data_table[ELECTRONIC_AUCTION_INDICATOR].apply(
            lambda x: 100 if x else 0)
        data_table[USE_OF_WTO_INDICATOR] = data_table[USE_OF_WTO_INDICATOR].apply(
            lambda x: 100 if x else 0)
        data_table[FUNDINGS_INFO_AVAILABLE_INDICATOR] = data_table[FUNDINGS_INFO_AVAILABLE_INDICATOR].apply(
            lambda x: 100 if x else 0)

        # add other indicators in calculate them
        data_table[IMPLEMENTATION_LOCATION_AVAILABLE_INDICATOR] = data_table.apply(
            lambda x: 100 if x[LOT_NUTS_COLUMN_NAME] else 0, axis=1)
        data_table[PRODUCT_CODES_AVAILABLE_INDICATOR] = data_table.apply(
            lambda x: 100 if x[LOT_CPV_COLUMN_NAME] else 0, axis=1)
        data_table[BIDDER_NAME_AVAILABLE_INDICATOR] = data_table.apply(
            lambda x: 100 if x[WINNER_NAME_COLUMN_NAME] else 0, axis=1)
        data_table[CONTRACT_VALUE_AVAILABLE_INDICATOR] = data_table.apply(
            lambda x: 100 if x[AMOUNT_VALUE_COLUMN_NAME] else 0, axis=1)
        data_table[PROCEDURE_TYPE_INDICATOR] = data_table.apply(
            lambda x: 100 if x[PROCEDURE_TYPE_COLUMN_NAME] == 'open' else 0, axis=1)

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


if __name__ == "__main__":
    etl = TedDataETLPipeline()
    etl.set_metadata({"start_date": "20160716", "end_date": "20160716"})
    df = etl.extract()['data']
    # print(df.to_string())
    df = etl.transform({"data": df})['data']
    print(df.to_string())
