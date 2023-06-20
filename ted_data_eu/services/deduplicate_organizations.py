import pandas as pd
import requests

from ted_data_eu import config
from ted_data_eu.adapters.master_data_registry import MasterDataRegistryAdapter


def get_organization_records_links(organizations: pd.DataFrame,
                                   unique_column_name: str,
                                   threshold_match_probability: float = 0.8,
                                   reference_table_name: str = None,
                                   linkage_model_config: dict = None,
                                   ) -> pd.DataFrame:
    """
    Links a dataframe of organization records.
    :param organizations: A dataframe of organizations.
    :param unique_column_name: The name of the column that contains unique values.
    :param threshold_match_probability: The minimum probability for a match.
    :param reference_table_name: The name of the reference table in the registry.
    :param linkage_model_config: A dictionary of the linkage model configuration.
    :return: A dataframe of links for the organizations.
    """
    master_data_registry = MasterDataRegistryAdapter(api_url=config.MASTER_DATA_REGISTRY_API_URL,
                                                     username=config.MASTER_DATA_REGISTRY_API_USER,
                                                     password=config.MASTER_DATA_REGISTRY_API_PASSWORD)
    return master_data_registry.dedupe_and_link(data=organizations,
                                                unique_column_name=unique_column_name,
                                                threshold_match_probability=threshold_match_probability,
                                                reference_table_name=reference_table_name,
                                                linkage_model_config=linkage_model_config)


def remove_reference_table(reference_table_name: str) -> bool:
    """
    Removes a reference table from the master data registry.
    :param reference_table_name: The name of the reference table.
    :return: True if the reference table was removed, False otherwise.
    """
    master_data_registry = MasterDataRegistryAdapter(api_url=config.MASTER_DATA_REGISTRY_API_URL,
                                                     username=config.MASTER_DATA_REGISTRY_API_USER,
                                                     password=config.MASTER_DATA_REGISTRY_API_PASSWORD)
    return master_data_registry.remove_reference_table(reference_table_name=reference_table_name)