from concurrent.futures import ThreadPoolExecutor

import rdflib
from airflow.decorators import dag, task
from airflow.timetables.trigger import CronTriggerTimetable
from pymongo import MongoClient
from ted_sws.event_manager.services.log import log_notice_error, log_error

from dags import DEFAULT_DAG_ARGUMENTS
from dags.dags_utils import get_dag_param, chunks, batched
from ted_sws import config
from ted_sws.core.model.notice import NoticeStatus
from ted_sws.data_manager.adapters.notice_repository import NoticeRepository
from ted_sws.notice_publisher_triple_store.services.load_transformed_notice_into_triple_store import \
    DEFAULT_NOTICE_RDF_MANIFESTATION_MIME_TYPE

from ted_data_eu.adapters.triple_store import GraphDBAdapter

GRAPHDB_REPOSITORY_NAME_DAG_PARAM_KEY = "graphdb_repository_name"
NOTICE_STATUS_DAG_PARAM_KEY = "notice_status"
DEFAULT_GRAPHDB_DATASET_NAME = "notices"
PUBLISH_NOTICE_BATCH_SIZE = 100


@dag(default_args=DEFAULT_DAG_ARGUMENTS,
     catchup=False,
     timetable=CronTriggerTimetable('0 5 * * *', timezone='UTC'),
     tags=['load', 'notices', 'graphdb'])
def load_notices_in_graphdb():
    @task
    def load_rdf_manifestations_in_graphdb():
        """

        :return:
        """
        graphdb_dataset_name = get_dag_param(key=GRAPHDB_REPOSITORY_NAME_DAG_PARAM_KEY,
                                             default_value=DEFAULT_GRAPHDB_DATASET_NAME)
        notice_status = get_dag_param(key=NOTICE_STATUS_DAG_PARAM_KEY, default_value=str(NoticeStatus.TRANSFORMED))
        mongodb_client = MongoClient(config.MONGO_DB_AUTH_URL)
        notice_repository = NoticeRepository(mongodb_client=mongodb_client)
        graphdb_repository = GraphDBAdapter()
        if graphdb_dataset_name not in graphdb_repository.list_repositories():
            graphdb_repository.create_repository(repository_name=graphdb_dataset_name)
        notices = notice_repository.get_notices_by_status(notice_status=NoticeStatus[notice_status])

        def batch_graphdb_loader(notices_batch: tuple):
            result_graph = rdflib.Graph()
            eligible_notices = []
            for notice in notices_batch:
                try:
                    tmp_graph = rdflib.Graph()
                    tmp_graph.parse(data=notice.rdf_manifestation.object_data, format="turtle")
                    result_graph = result_graph + tmp_graph
                    eligible_notices.append(notice)
                except Exception as e:
                    notice._status = NoticeStatus.INELIGIBLE_FOR_PUBLISHING
                    notice_repository.update(notice)
                    notice_normalised_metadata = notice.normalised_metadata if notice else None
                    log_notice_error(message=f"Error to parse notice {notice.ted_id} rdf manifestation: {e}",
                                     notice_id=notice.ted_id, domain_action="load_notice_in_graphdb",
                                     notice_form_number=notice_normalised_metadata.form_number if notice_normalised_metadata else None,
                                     notice_status=notice.status if notice else None,
                                     notice_eforms_subtype=notice_normalised_metadata.eforms_subtype if notice_normalised_metadata else None)
            try:
                rdf_manifestation_string = result_graph.serialize(format="turtle").encode(encoding='utf-8')
                graphdb_repository.add_data_to_repository(file_content=rdf_manifestation_string,
                                                          repository_name=graphdb_dataset_name,
                                                          mime_type=DEFAULT_NOTICE_RDF_MANIFESTATION_MIME_TYPE)

                for notice in eligible_notices:
                    notice._status = NoticeStatus.PUBLISHED
                    notice_repository.update(notice)
            except Exception as e:
                log_error(message=f"Error to load notices in graphdb: {e}")


        notice_batches = batched(notices, PUBLISH_NOTICE_BATCH_SIZE)
        features = []
        with ThreadPoolExecutor(max_workers=16) as executor:
            for notice_batch in notice_batches:
               feature = executor.submit(batch_graphdb_loader, notice_batch)
               features.append(feature)
            for feature in features:
                feature.result()

    load_rdf_manifestations_in_graphdb()


dag = load_notices_in_graphdb()
