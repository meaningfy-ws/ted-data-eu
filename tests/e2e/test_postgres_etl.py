import pandas as pd
import sqlalchemy

from ted_data_eu import config
from ted_data_eu.services.etl_pipelines.postgres_etl_pipeline import PostgresETLPipeline


def test_postgres_pipeline(graphdb_triple_store, example_notices,
                           tmp_repository_name, etl_pipeline_config):
    graphdb_repositories = graphdb_triple_store.list_repositories()
    if tmp_repository_name in graphdb_repositories:
        graphdb_triple_store.delete_repository(tmp_repository_name)
    graphdb_triple_store.create_repository(tmp_repository_name)
    for example_notice in example_notices:
        graphdb_triple_store.add_file_to_repository(example_notice, repository_name=tmp_repository_name)

    for table_name, query_path in config.TABLE_QUERY_PATHS.items():
        postgres_etl_pipeline = PostgresETLPipeline(table_name=table_name, sparql_query_path=query_path, primary_key_column_name=f"{table_name}Id")
        table_name += '_test'
        postgres_etl_pipeline.set_metadata(etl_pipeline_config)
        test_data = postgres_etl_pipeline.extract()['data']
        assert isinstance(test_data, pd.DataFrame)
        assert not test_data.empty

        test_data = postgres_etl_pipeline.transform({"data": test_data})['data']
        assert isinstance(test_data, pd.DataFrame)
        assert not test_data.empty

        postgres_etl_pipeline.load({"data": test_data})

        assert sqlalchemy.inspect(postgres_etl_pipeline.sql_engine).has_table(postgres_etl_pipeline.table_name) is True

        with postgres_etl_pipeline.sql_engine.connect() as sql_connection:
            sql_connection.execute(f"DROP TABLE IF EXISTS \"{postgres_etl_pipeline.table_name}\";")

    graphdb_triple_store.delete_repository(tmp_repository_name)
