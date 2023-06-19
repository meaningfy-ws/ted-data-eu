import io
import tempfile
from pathlib import Path

import pandas as pd
import sqlalchemy

from ted_data_eu import config
from ted_data_eu.services.etl_pipelines.postgres_etl_pipeline import PostgresETLPipeline, CellarETLPipeline, DATA_FIELD, \
    SKIP_NEXT_STEP_FIELD, DROP_TABLE_IF_EXISTS_QUERY

TEST_TABLE_NAME_EXTENSION = "_test"
QUERY_LIMIT = "LIMIT 100"


def test_postgres_pipeline(graphdb_triple_store, example_notices,
                           tmp_repository_name, etl_pipeline_config):
    graphdb_repositories = graphdb_triple_store.list_repositories()
    if tmp_repository_name in graphdb_repositories:
        graphdb_triple_store.delete_repository(tmp_repository_name)
    graphdb_triple_store.create_repository(tmp_repository_name)
    for example_notice in example_notices:
        graphdb_triple_store.add_file_to_repository(example_notice, repository_name=tmp_repository_name)
    tables_metadata = config.TABLES_METADATA
    for table_name, query_path in config.TRIPLE_STORE_TABLE_QUERY_PATHS.items():
        postgres_etl_pipeline = PostgresETLPipeline(table_name=f"{table_name}{TEST_TABLE_NAME_EXTENSION}",
                                                    sparql_query_path=query_path,
                                                    primary_key_column_name=tables_metadata[table_name]['PK'],
                                                    foreign_key_column_names=tables_metadata[table_name]['FK'],
                                                    triple_store=graphdb_triple_store,
                                                    triple_store_endpoint=tmp_repository_name)
        with postgres_etl_pipeline.sql_engine.connect() as sql_connection:
            sql_connection.execute(DROP_TABLE_IF_EXISTS_QUERY.format(table_name=postgres_etl_pipeline.table_name))
        postgres_etl_pipeline.set_metadata(etl_pipeline_config)
        test_data = postgres_etl_pipeline.extract()[DATA_FIELD]
        assert isinstance(test_data, io.StringIO)
        assert len(test_data.getvalue()) > 0

        test_data = postgres_etl_pipeline.transform({DATA_FIELD: test_data})[DATA_FIELD]
        assert isinstance(test_data, pd.DataFrame)
        assert not test_data.empty

        postgres_etl_pipeline.load({DATA_FIELD: test_data})

        assert sqlalchemy.inspect(postgres_etl_pipeline.sql_engine).has_table(postgres_etl_pipeline.table_name) is True

        with postgres_etl_pipeline.sql_engine.connect() as sql_connection:
            sql_connection.execute(f"DROP TABLE IF EXISTS \"{postgres_etl_pipeline.table_name}\";")

    graphdb_triple_store.delete_repository(tmp_repository_name)


def test_cellar_etl_pipeline():
    tables_metadata = config.TABLES_METADATA
    for table_name, query_path in config.CELLAR_TABLE_QUERY_PATHS.items():
        with tempfile.NamedTemporaryFile() as tmp_file:
            sparql_query = query_path.read_text(encoding='utf-8')
            sparql_query += QUERY_LIMIT
            tmp_file.write(sparql_query.encode())
            tmp_file.seek(0)
            query_path = Path(tmp_file.name)
            cellar_etl_pipeline = CellarETLPipeline(table_name=f"{table_name}{TEST_TABLE_NAME_EXTENSION}",
                                                    sparql_query_path=query_path,
                                                    primary_key_column_name=tables_metadata[table_name]['PK'],
                                                    foreign_key_column_names=tables_metadata[table_name]['FK'])
            with cellar_etl_pipeline.sql_engine.connect() as sql_connection:
                sql_connection.execute(DROP_TABLE_IF_EXISTS_QUERY.format(table_name=cellar_etl_pipeline.table_name))
            test_data = cellar_etl_pipeline.extract()[DATA_FIELD]
            assert isinstance(test_data, io.StringIO)
            assert len(test_data.getvalue()) > 0
            cellar_etl_pipeline.table_name = cellar_etl_pipeline.table_name.replace(TEST_TABLE_NAME_EXTENSION, "")
            test_data = cellar_etl_pipeline.transform({DATA_FIELD: test_data})[DATA_FIELD]
            cellar_etl_pipeline.table_name = f"{table_name}{TEST_TABLE_NAME_EXTENSION}"
            assert isinstance(test_data, pd.DataFrame)
            assert not test_data.empty

            cellar_etl_pipeline.load({DATA_FIELD: test_data})

            test_data = cellar_etl_pipeline.extract()
            assert test_data.get(SKIP_NEXT_STEP_FIELD, False) is True

            assert sqlalchemy.inspect(cellar_etl_pipeline.sql_engine).has_table(cellar_etl_pipeline.table_name) is True

            with cellar_etl_pipeline.sql_engine.connect() as sql_connection:
                sql_connection.execute(f"DROP TABLE IF EXISTS \"{cellar_etl_pipeline.table_name}\";")
