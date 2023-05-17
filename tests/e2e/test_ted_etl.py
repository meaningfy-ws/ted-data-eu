import pandas as pd

from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import AMOUNT_VALUE_EUR_COLUMN_NAME, NOTICE_LINK, \
    SUBCONTRACT_AVAILABLE_INDICATOR, DURATION_AVAILABLE_INDICATOR, JOINT_PROCUREMENT_INDICATOR, \
    USE_OF_FRAMEWORK_AGREEMENT_INDICATOR, ELECTRONIC_AUCTION_INDICATOR, USE_OF_WTO_INDICATOR, \
    IMPLEMENTATION_LOCATION_AVAILABLE_INDICATOR, FUNDINGS_INFO_AVAILABLE_INDICATOR, BIDDER_NAME_AVAILABLE_INDICATOR, \
    CONTRACT_VALUE_AVAILABLE_INDICATOR, PROCEDURE_TYPE_INDICATOR, PRODUCT_CODES_AVAILABLE_INDICATOR, LOT_NUTS_0, \
    LOT_NUTS_1, LOT_NUTS_2, LOT_NUTS_3, get_country_name_by_code, BUYER_NUTS_COLUMN_NAME, PROCEDURE_ID_COLUMN_NAME, \
    PROCEDURE_DESCRIPTION_COLUMN_NAME, PROCEDURE_COLUMN_NAME, TDA_FREE_INDEX_NAME, TDA_STARTER_INDEX_NAME, CPV_RANK_4, \
    CPV_RANK_2, CPV_RANK_1, CPV_RANK_3, LOT_COUNTRY


def test_get_country_name_by_code(real_country_code_alpha_2, fake_country_code_alpha_2, real_country_code_alpha_3,
                                  fake_country_code_alpha_3):
    assert get_country_name_by_code(real_country_code_alpha_2) == "Spain"
    assert get_country_name_by_code(fake_country_code_alpha_2) is None
    assert get_country_name_by_code(real_country_code_alpha_3) == "Spain"
    assert get_country_name_by_code(fake_country_code_alpha_3) is None


def test_etl_pipeline(ted_data_etl_pipelines, etl_pipeline_config, graphdb_triple_store, example_notices,
                      tmp_repository_name):
    for ted_data_etl_pipeline in ted_data_etl_pipelines:
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
        assert LOT_COUNTRY in dataframe_columns


        assert BUYER_NUTS_COLUMN_NAME in dataframe_columns
        assert PROCEDURE_ID_COLUMN_NAME in dataframe_columns
        assert PROCEDURE_DESCRIPTION_COLUMN_NAME in dataframe_columns
        assert PROCEDURE_COLUMN_NAME in dataframe_columns

        if ted_data_etl_pipeline == TDA_FREE_INDEX_NAME or ted_data_etl_pipeline == TDA_STARTER_INDEX_NAME:
            assert LOT_NUTS_2 not in dataframe_columns
            assert LOT_NUTS_3 not in dataframe_columns

            assert CPV_RANK_4 not in dataframe_columns
            assert CPV_RANK_3 not in dataframe_columns
            assert CPV_RANK_2 not in dataframe_columns
            if ted_data_etl_pipeline == TDA_FREE_INDEX_NAME:
                assert CPV_RANK_1 not in dataframe_columns
                assert LOT_NUTS_1 not in dataframe_columns

        ted_data_etl_pipeline.load(data)

        graphdb_triple_store.delete_repository(tmp_repository_name)
