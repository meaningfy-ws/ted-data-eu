from airflow.decorators import dag
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup

from dags import DEFAULT_DAG_ARGUMENTS
from dags.operators.ETLStepOperator import ExtractStepOperator, TransformStepOperator, LoadStepOperator
from ted_data_eu import config
from ted_data_eu.adapters.etl_pipeline_register import ETLPipelineRegister
from ted_data_eu.services.etl_pipelines.postgres_etl_pipeline import PostgresETLPipeline, CellarETLPipeline
from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import TDA_FREE_INDEX_NAME, TedDataETLPipeline, \
    TDA_STARTER_INDEX_NAME, TDA_PREMIUM_INDEX_NAME

etl_pipelines_register = ETLPipelineRegister()

ETL_EXECUTOR_DAG_NAME = 'etl_executor'

MAX_ETL_ACTIVE_RUNS = 1
MAX_ETL_ACTIVE_TASKS = 1

PRIMARY_KEY_COLUMN_NAME = 'PK'
FOREIGN_KEY_COLUMN_NAMES = 'FK'


def init_etl_pipelines_register():
    """
        This function is used for register all ETL pipelines inside DAG.
    :return:
    """
    etl_pipelines_register.register(etl_pipeline_name=TDA_FREE_INDEX_NAME,
                                    etl_pipeline=TedDataETLPipeline(business_pack_name=TDA_FREE_INDEX_NAME))
    etl_pipelines_register.register(etl_pipeline_name=TDA_STARTER_INDEX_NAME,
                                    etl_pipeline=TedDataETLPipeline(business_pack_name=TDA_STARTER_INDEX_NAME))
    etl_pipelines_register.register(etl_pipeline_name=TDA_PREMIUM_INDEX_NAME,
                                    etl_pipeline=TedDataETLPipeline(business_pack_name=TDA_PREMIUM_INDEX_NAME))

    tables_metadata = config.TABLES_METADATA

    for table_name, query_path in config.TRIPLE_STORE_TABLE_QUERY_PATHS.items():
        etl_pipelines_register.register(etl_pipeline_name=table_name,
                                        etl_pipeline=PostgresETLPipeline(table_name=table_name,
                                                                         sparql_query_path=query_path,
                                                                         primary_key_column_name=
                                                                         tables_metadata[table_name][
                                                                             PRIMARY_KEY_COLUMN_NAME],
                                                                         foreign_key_column_names=
                                                                         tables_metadata[table_name][
                                                                             FOREIGN_KEY_COLUMN_NAMES]))

    for table_name, query_path in config.CELLAR_TABLE_QUERY_PATHS.items():
        etl_pipelines_register.register(etl_pipeline_name=table_name,
                                        etl_pipeline=CellarETLPipeline(table_name=table_name,
                                                                       sparql_query_path=query_path,
                                                                       primary_key_column_name=
                                                                       tables_metadata[table_name][
                                                                           PRIMARY_KEY_COLUMN_NAME],
                                                                       foreign_key_column_names=
                                                                       tables_metadata[table_name][
                                                                           FOREIGN_KEY_COLUMN_NAMES]))


@dag(default_args=DEFAULT_DAG_ARGUMENTS,
     schedule_interval=None,
     max_active_runs=MAX_ETL_ACTIVE_RUNS,
     max_active_tasks=MAX_ETL_ACTIVE_TASKS,
     tags=['etl', 'executor'])
def etl_executor():
    """

    :return:
    """
    start_step = EmptyOperator(task_id='start')
    end_step = EmptyOperator(task_id='end')
    init_etl_pipelines_register()
    for etl_pipeline_name, etl_pipeline in etl_pipelines_register.pipelines_register.items():
        with TaskGroup(group_id=etl_pipeline_name.replace(" ", "_")) as task_group:
            extract_step = ExtractStepOperator(task_id="extract", etl_pipeline=etl_pipeline)
            transform_step = TransformStepOperator(task_id="transform", etl_pipeline=etl_pipeline)
            load_step = LoadStepOperator(task_id="load", etl_pipeline=etl_pipeline)
            extract_step >> transform_step >> load_step
            start_step >> task_group >> end_step


dag = etl_executor()
