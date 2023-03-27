from datetime import datetime
from typing import Any
from dateutil import rrule

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from dags import DEFAULT_DAG_ARGUMENTS
from dags.dags_utils import get_dag_param
from dags.fetch_notices_by_date import WILD_CARD_DAG_KEY, TRIGGER_COMPLETE_WORKFLOW_DAG_KEY, \
    DAG_NAME as FETCH_NOTICES_BY_DATE_DAG_NAME
from ted_sws.event_manager.adapters.event_log_decorator import event_log
from ted_sws.event_manager.model.event_message import TechnicalEventMessage, EventMessageMetadata, \
    EventMessageProcessType

from dags.operators.ETLStepOperator import ETL_METADATA_DAG_CONFIG_KEY
from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import START_DATE_METADATA_FIELD, END_DATE_METADATA_FIELD, \
    TED_DATA_ETL_PIPELINE_NAME, generate_dates_by_date_range

ETL_EXECUTOR_DAG_NAME = "etl_executor"

RUN_ETL_EXECUTOR_BY_DATE_RANGE_DAG_NAME = "run_etl_executor_by_date_range"


@dag(default_args=DEFAULT_DAG_ARGUMENTS, schedule_interval=None, tags=['master'])
def run_etl_executor_by_date_range():
    @task
    @event_log(TechnicalEventMessage(
        message="trigger_run_etl_executor_by_date_range",
        metadata=EventMessageMetadata(
            process_type=EventMessageProcessType.DAG, process_name=RUN_ETL_EXECUTOR_BY_DATE_RANGE_DAG_NAME
        ))
    )
    def run_etl_executor_for_each_date_in_range():
        context: Any = get_current_context()
        start_date = get_dag_param(key=START_DATE_METADATA_FIELD, raise_error=True)
        end_date = get_dag_param(key=END_DATE_METADATA_FIELD, raise_error=True)

        date_range = generate_dates_by_date_range(start_date, end_date)
        for date in date_range:
            TriggerDagRunOperator(
                task_id=f'trigger_run_etl_pipeline_dag_{date}',
                trigger_dag_id=FETCH_NOTICES_BY_DATE_DAG_NAME,
                conf={ETL_METADATA_DAG_CONFIG_KEY:
                          {TED_DATA_ETL_PIPELINE_NAME:
                               {START_DATE_METADATA_FIELD: date, END_DATE_METADATA_FIELD: date}
                           }
                      }
            ).execute(context=context)

    run_etl_executor_for_each_date_in_range()


dag = run_etl_executor_by_date_range()
