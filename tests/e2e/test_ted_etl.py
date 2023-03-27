import pandas as pd

from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import TED_DATA_COLUMNS


def check_tda_etl_columns(data_columns: list):
    for column in TED_DATA_COLUMNS:
        assert column in data_columns


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

    check_tda_etl_columns(list(dataframe.columns))

    data = ted_data_etl_pipeline.transform(data)
    dataframe = data['data']
    check_tda_etl_columns(list(dataframe.columns))

    ted_data_etl_pipeline.load(data)

    graphdb_triple_store.delete_repository(tmp_repository_name)
