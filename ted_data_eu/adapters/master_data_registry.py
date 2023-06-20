import pandas as pd
import requests

DATAFRAME_TO_JSON_ORIENT_TYPE = "split"
UNIQUE_ID_SRC_COLUMN_NAME = "unique_id_src"
UNIQUE_ID_DST_COLUMN_NAME = "unique_id_dst"
MATCH_PROBABILITY_COLUMN_NAME = "match_probability"

class MasterDataRegistryAdapter:

    def __init__(self, api_url: str = None,
                 username: str = None,
                 password: str = None):
        """
        Initializes a MasterDataRegistryAdapter.
        """
        self.api_url = api_url
        self.username = username
        self.password = password

    def dedupe_and_link(self,
                        data: pd.DataFrame,
                        unique_column_name: str,
                        threshold_match_probability: float = 0.8,
                        reference_table_name: str = None,
                        linkage_model_config: dict = None,
                        ) -> pd.DataFrame:
        """
        Links a dataframe of records.
        :param data: A dataframe of records.
        :param unique_column_name: The name of the column that contains unique values.
        :param threshold_match_probability: The minimum probability for a match.
        :param reference_table_name: The name of the reference table in the registry.
        :param linkage_model_config: A dictionary of the linkage model configuration.
        :return: A dataframe of links for the records.
        """
        response = requests.post(f"{self.api_url}/api/v1/dedup_and_link",
                                 json={
                                     "dataframe_json": data.to_json(orient=DATAFRAME_TO_JSON_ORIENT_TYPE),
                                     "unique_column_name": unique_column_name,
                                     "threshold_match_probability": threshold_match_probability,
                                     "reference_table_name": reference_table_name,
                                     "linkage_model_config": linkage_model_config
                                 },
                                 auth=(self.username, self.password)
                                 )
        if response.status_code == 200:
            links_for_records = pd.read_json(response.json(), orient=DATAFRAME_TO_JSON_ORIENT_TYPE)
            return links_for_records
        else:
            raise Exception(f"Error linking records: {response.status_code} \n {response.text}")

    def remove_reference_table(self, reference_table_name: str) -> bool:
        """
        Removes a reference table from the registry.
        :param reference_table_name: The name of the reference table.
        :return: True if the reference table was removed, False otherwise.
        """
        response = requests.post(f"{self.api_url}/api/v1/reference_tables/remove",
                                 json={"reference_table_name": reference_table_name},
                                 auth=(self.username, self.password)
                                 )
        if response.status_code == 200:
            return response.json()["remove_result"]
        else:
            return False
