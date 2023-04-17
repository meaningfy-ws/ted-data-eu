import pandas as pd

from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import AMOUNT_VALUE_EUR_COLUMN_NAME, NOTICE_LINK, \
    SUBCONTRACT_AVAILABLE_INDICATOR, DURATION_AVAILABLE_INDICATOR, JOINT_PROCUREMENT_INDICATOR, \
    USE_OF_FRAMEWORK_AGREEMENT_INDICATOR, ELECTRONIC_AUCTION_INDICATOR, USE_OF_WTO_INDICATOR, \
    IMPLEMENTATION_LOCATION_AVAILABLE_INDICATOR, FUNDINGS_INFO_AVAILABLE_INDICATOR, BIDDER_NAME_AVAILABLE_INDICATOR, \
    CONTRACT_VALUE_AVAILABLE_INDICATOR, PROCEDURE_TYPE_INDICATOR, PRODUCT_CODES_AVAILABLE_INDICATOR, LOT_NUTS_0, \
    LOT_NUTS_1, LOT_NUTS_2, LOT_NUTS_3



def test_etl_pipeline(ted_data_etl_pipeline, etl_pipeline_config, graphdb_triple_store, example_notices,
                      tmp_repository_name):
    graphdb_repositories = graphdb_triple_store.list_repositories()
    if tmp_repository_name in graphdb_repositories:
        graphdb_triple_store.delete_repository(tmp_repository_name)
    graphdb_triple_store.create_repository(tmp_repository_name)
    for example_notice in example_notices:
        graphdb_triple_store.add_file_to_repository(example_notice, repository_name=tmp_repository_name)

    ted_data_etl_pipeline.set_metadata(etl_pipeline_config)
    data = ted_data_etl_pipeline.extract()
    dataframe = data['data']
    assert isinstance(dataframe, pd.DataFrame)
    assert not dataframe.empty

    data = ted_data_etl_pipeline.transform(data)
    dataframe = data['data']

    dataframe_columns = list(dataframe.columns)
    assert AMOUNT_VALUE_EUR_COLUMN_NAME in dataframe_columns
    assert NOTICE_LINK in dataframe_columns
    assert SUBCONTRACT_AVAILABLE_INDICATOR in dataframe_columns
    assert DURATION_AVAILABLE_INDICATOR in dataframe_columns
    assert JOINT_PROCUREMENT_INDICATOR in dataframe_columns
    assert USE_OF_FRAMEWORK_AGREEMENT_INDICATOR in dataframe_columns
    assert ELECTRONIC_AUCTION_INDICATOR in dataframe_columns
    assert USE_OF_WTO_INDICATOR in dataframe_columns
    assert IMPLEMENTATION_LOCATION_AVAILABLE_INDICATOR in dataframe_columns
    assert FUNDINGS_INFO_AVAILABLE_INDICATOR in dataframe_columns
    assert PRODUCT_CODES_AVAILABLE_INDICATOR in dataframe_columns
    assert BIDDER_NAME_AVAILABLE_INDICATOR in dataframe_columns
    assert CONTRACT_VALUE_AVAILABLE_INDICATOR in dataframe_columns
    assert PROCEDURE_TYPE_INDICATOR in dataframe_columns

    assert LOT_NUTS_0 in dataframe_columns
    assert LOT_NUTS_1 in dataframe_columns
    assert LOT_NUTS_2 in dataframe_columns
    assert LOT_NUTS_3 in dataframe_columns

    ted_data_etl_pipeline.load(data)

    graphdb_triple_store.delete_repository(tmp_repository_name)
