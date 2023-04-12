from airflow.decorators import dag, task
from pymongo import MongoClient
from ted_sws.event_manager.services.log import log_notice_error

from dags import DEFAULT_DAG_ARGUMENTS
from dags.dags_utils import get_dag_param
from ted_sws import config
from ted_sws.core.model.notice import NoticeStatus
from ted_sws.data_manager.adapters.notice_repository import NoticeRepository
from ted_sws.notice_publisher_triple_store.services.load_transformed_notice_into_triple_store import \
    load_rdf_manifestation_into_triple_store

from ted_data_eu.adapters.triple_store import GraphDBAdapter

GRAPHDB_REPOSITORY_NAME_DAG_PARAM_KEY = "graphdb_repository_name"
NOTICE_STATUS_DAG_PARAM_KEY = "notice_status"
DEFAULT_GRAPHDB_DATASET_NAME = "notices"


@dag(default_args=DEFAULT_DAG_ARGUMENTS,
     schedule_interval=None,
     tags=['load', 'notices', 'graphdb'])
def load_notices_in_graphdb():
    @task
    def load_distilled_rdf_manifestations_in_graphdb():
        """

        :return:
        """
        graphdb_dataset_name = get_dag_param(key=GRAPHDB_REPOSITORY_NAME_DAG_PARAM_KEY,
                                             default_value=DEFAULT_GRAPHDB_DATASET_NAME)
        notice_status = get_dag_param(key=NOTICE_STATUS_DAG_PARAM_KEY, default_value=str(NoticeStatus.TRANSFORMED))
        mongodb_client = MongoClient(config.MONGO_DB_AUTH_URL)
        notice_repository = NoticeRepository(mongodb_client=mongodb_client)
        graphdb_repository = GraphDBAdapter()
        notices = notice_repository.get_notices_by_status(notice_status=NoticeStatus[notice_status])

        for notice in notices:
            try:
                load_rdf_manifestation_into_triple_store(rdf_manifestation=notice.rdf_manifestation,
                                                         triple_store_repository=graphdb_repository,
                                                         repository_name=graphdb_dataset_name)
                notice._status = NoticeStatus.PUBLISHED
                notice_repository.update(notice)
            except Exception as e:
                notice._status = NoticeStatus.INELIGIBLE_FOR_PUBLISHING
                notice_repository.update(notice)
                notice_normalised_metadata = notice.normalised_metadata if notice else None
                log_notice_error(message=f"Error while loading notice {notice.ted_id} in graphdb: {e}",
                                 notice_id=notice.ted_id, domain_action="load_notice_in_graphdb",
                                 notice_form_number=notice_normalised_metadata.form_number if notice_normalised_metadata else None,
                                 notice_status=notice.status if notice else None,
                                 notice_eforms_subtype=notice_normalised_metadata.eforms_subtype if notice_normalised_metadata else None)


    load_distilled_rdf_manifestations_in_graphdb()


dag = load_notices_in_graphdb()
