from airflow.decorators import dag, task
from pymongo import MongoClient
from ted_sws.data_manager.adapters.notice_repository import NoticeRepository

from dags import DEFAULT_DAG_ARGUMENTS
from dags.dags_utils import get_dag_param
from dags.pipelines.notice_selectors_pipelines import notice_ids_selector_by_status
from ted_sws.core.model.notice import NoticeStatus
from ted_sws.event_manager.adapters.event_log_decorator import event_log
from ted_sws.event_manager.model.event_message import TechnicalEventMessage, EventMessageMetadata, \
    EventMessageProcessType

from ted_data_eu import config

DAG_NAME = "reset_notices_status"

FORM_NUMBER_DAG_PARAM = "form_number"
START_DATE_DAG_PARAM = "start_date"
END_DATE_DAG_PARAM = "end_date"
XSD_VERSION_DAG_PARAM = "xsd_version"
SOURCE_NOTICE_STATUS_DAG_PARAM = "source_notice_status"
TARGET_NOTICE_STATUS_DAG_PARAM = "target_notice_status"

@dag(default_args=DEFAULT_DAG_ARGUMENTS,
     schedule_interval=None,
     tags=['selector', 'raw-notices'])
def reset_notices_status():
    @task
    @event_log(TechnicalEventMessage(
        message="reset_notices_status",
        metadata=EventMessageMetadata(
            process_type=EventMessageProcessType.DAG, process_name=DAG_NAME
        ))
    )
    def reset_notices_status_based_on_source_and_target_status():
        """
            This task is used to reset notices status based on source and target status.
        :return:
        """
        source_notice_status = get_dag_param(key=SOURCE_NOTICE_STATUS_DAG_PARAM, raise_error=True)
        target_notice_status = get_dag_param(key=TARGET_NOTICE_STATUS_DAG_PARAM, raise_error=True)
        start_date = get_dag_param(key=START_DATE_DAG_PARAM)
        end_date = get_dag_param(key=END_DATE_DAG_PARAM)
        xsd_version = get_dag_param(key=XSD_VERSION_DAG_PARAM)
        notice_ids = notice_ids_selector_by_status(notice_statuses=[NoticeStatus[source_notice_status]], start_date=start_date,
                                                   end_date=end_date, xsd_version=xsd_version)

        notice_repository = NoticeRepository(mongodb_client=MongoClient(config.MONGO_DB_AUTH_URL))
        for notice_id in notice_ids:
            notice = notice_repository.get(reference=notice_id)
            notice.update_status_to(new_status=NoticeStatus[target_notice_status])
            notice_repository.update(notice=notice)

    reset_notices_status_based_on_source_and_target_status()


dag = reset_notices_status()
