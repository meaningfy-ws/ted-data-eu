import re
from pathlib import Path
from typing import Dict
import sqlalchemy
from pandas import DataFrame

from ted_data_eu import config, PROJECT_RESOURCES_BQ_FOLDER_PATH
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC
from ted_data_eu.adapters.triple_store import GraphDBAdapter

TED_NOTICES_LINK = 'https://ted.europa.eu/udl?uri=TED:NOTICE:{notice_id}:TEXT:EN:HTML'
TRIPLE_STORE_ENDPOINT = "notices"


def generate_link_to_notice(notice_uri: str):
    """
        Generates the link to the notice from the Notice URI
        :param notice_uri: URI of the lot as str
        :return: Link to the notice as str

        example Notice URI: epd:id_2015-S-250-456405_Notice
    """
    lot_id = re.search(r"id_(.*)_Notice", notice_uri).group(1)
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

    def __init__(self, table_name: str, sparql_query_path: Path):
        """
            Constructor
        """
        self.etl_metadata = {}
        self.table_name = table_name
        self.sparql_query_path = sparql_query_path

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
        sparql_query_str = self.sparql_query_path.read_text(encoding="utf-8")
        triple_store_endpoint = GraphDBAdapter().get_sparql_triple_store_endpoint(repository_name=TRIPLE_STORE_ENDPOINT)
        result_table = triple_store_endpoint.with_query(sparql_query_str).fetch_tabular()
        return {"data": result_table}

    def transform(self, extracted_data: Dict) -> Dict:
        # TODO: transform step
        return {"data": extracted_data["data"]}

    def load(self, transformed_data: Dict):
        data_table: DataFrame = transformed_data["data"]
        sql_engine = sqlalchemy.create_engine('', echo=False) # TODO: to add sql endpoint to .env
        with sql_engine.connect() as sql_connection:
            data_table.to_sql(self.table_name, con=sql_connection, if_exists='replace')
        return {"data": transformed_data["data"]}


# Test
if __name__ == "__main__":
    etl = PostgresETLPipeline(table_name="NUTS", sparql_query_path=PROJECT_RESOURCES_BQ_FOLDER_PATH / "postgres_tables" / "NUTS.rq")
    #etl.set_metadata({"start_date": "20191031", "end_date": "20191031"})
    df = etl.extract()['data']
    df = etl.transform({"data": df})['data']
    print(df.to_string())
