from airflow.decorators import dag
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup

from dags import DEFAULT_DAG_ARGUMENTS
from dags.operators.ETLStepOperator import ExtractStepOperator, TransformStepOperator, LoadStepOperator
from ted_data_eu.adapters.etl_pipeline_register import ETLPipelineRegister
from ted_data_eu.services.etl_pipelines.dummy_etl_pipeline import DummyETLPipeline, TestETLPipeline

etl_pipelines_register = ETLPipelineRegister()


def init_etl_pipelines_register():
    """
        This function is used for register all ETL pipelines inside DAG.
    :return:
    """
    etl_pipelines_register.register(etl_pipeline_name="Test ETL 1 pipeline", etl_pipeline=DummyETLPipeline())
    etl_pipelines_register.register(etl_pipeline_name="Test ETL 2 pipeline", etl_pipeline=TestETLPipeline())


@dag(default_args=DEFAULT_DAG_ARGUMENTS,
     schedule_interval=None,
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
