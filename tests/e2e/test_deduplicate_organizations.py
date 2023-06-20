from ted_data_eu.adapters.master_data_registry import MATCH_PROBABILITY_COLUMN_NAME, UNIQUE_ID_SRC_COLUMN_NAME
from ted_data_eu.services.deduplicate_organizations import get_organization_records_links, remove_reference_table


def test_deduplicate_organizations(duplicates_records_dataframe, reference_table_name,
                                   linkage_model_config,
                                   duplicates_records_unique_column_name):
    assert remove_reference_table(reference_table_name=reference_table_name)
    result_links = get_organization_records_links(organizations=duplicates_records_dataframe,
                                                  unique_column_name=duplicates_records_unique_column_name,
                                                  linkage_model_config=linkage_model_config,
                                                  reference_table_name=reference_table_name
                                                  )
    assert len(result_links) == len(duplicates_records_dataframe)
    assert result_links[MATCH_PROBABILITY_COLUMN_NAME].min() >= 0.8
    assert result_links[MATCH_PROBABILITY_COLUMN_NAME].max() <= 1.0
    assert all(result_links[UNIQUE_ID_SRC_COLUMN_NAME] == duplicates_records_dataframe[
        duplicates_records_unique_column_name])
    assert remove_reference_table(reference_table_name=reference_table_name)
