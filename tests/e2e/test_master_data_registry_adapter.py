from ted_data_eu import config
from ted_data_eu.adapters.master_data_registry import MasterDataRegistryAdapter, UNIQUE_ID_SRC_COLUMN_NAME, \
    UNIQUE_ID_DST_COLUMN_NAME, MATCH_PROBABILITY_COLUMN_NAME


def test_master_data_registry_remove_reference_table(reference_table_name):
    master_data_registry = MasterDataRegistryAdapter(api_url=config.MASTER_DATA_REGISTRY_API_URL,
                                                     username=config.MASTER_DATA_REGISTRY_API_USER,
                                                     password=config.MASTER_DATA_REGISTRY_API_PASSWORD,
                                                     )
    assert master_data_registry.remove_reference_table(reference_table_name=reference_table_name)


def test_master_data_registry_dedup_and_link(duplicates_records_dataframe, reference_table_name,
                                             linkage_model_config,
                                             duplicates_records_unique_column_name):
    master_data_registry = MasterDataRegistryAdapter(api_url=config.MASTER_DATA_REGISTRY_API_URL,
                                                     username=config.MASTER_DATA_REGISTRY_API_USER,
                                                     password=config.MASTER_DATA_REGISTRY_API_PASSWORD,
                                                     )
    assert master_data_registry.remove_reference_table(reference_table_name=reference_table_name)
    result_links = master_data_registry.dedupe_and_link(data=duplicates_records_dataframe,
                                                        unique_column_name=duplicates_records_unique_column_name,
                                                        linkage_model_config=linkage_model_config,
                                                        reference_table_name=reference_table_name
                                                        )

    assert len(result_links) == len(duplicates_records_dataframe)
    assert result_links[MATCH_PROBABILITY_COLUMN_NAME].min() >= 0.8
    assert result_links[MATCH_PROBABILITY_COLUMN_NAME].max() <= 1.0
    assert all(
        result_links[UNIQUE_ID_SRC_COLUMN_NAME] == duplicates_records_dataframe[duplicates_records_unique_column_name])
    assert UNIQUE_ID_SRC_COLUMN_NAME in result_links.columns
    assert UNIQUE_ID_DST_COLUMN_NAME in result_links.columns
    assert master_data_registry.remove_reference_table(reference_table_name=reference_table_name)
