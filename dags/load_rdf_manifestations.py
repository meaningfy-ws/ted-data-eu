from airflow.decorators import dag, task
from datetime import datetime, timedelta
from pymongo import MongoClient
from ted_sws import config
from ted_sws.data_manager.adapters.notice_repository import NoticeRepository
from ted_sws.data_manager.adapters.triple_store import AllegroGraphTripleStore

TDA_REPOSITORY_NAME = "tda_repository_test"

DEFAULT_DAG_ARGUMENTS = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2022, 1, 1),
    "email": ["info@meaningfy.ws"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=3600),
    "max_active_runs": 15,
    "concurrency": 15,
    "execution_timeout": timedelta(days=10),
}


@dag(default_args=DEFAULT_DAG_ARGUMENTS,
     schedule_interval=None,
     tags=['mongodb', 'agraph'])
def load_rdf_manifestations():
    @task(multiple_outputs=True)
    def get_manifestation_from_mongodb():
        mongodb_client = MongoClient(config.MONGO_DB_AUTH_URL)
        notice_repository = NoticeRepository(mongodb_client=mongodb_client)
        notices_distilled_rdf_manifestation = {notice.ted_id: notice.distilled_rdf_manifestation.object_data for notice
                                               in notice_repository.list() if notice.distilled_rdf_manifestation}
        if not notices_distilled_rdf_manifestation:
            raise Exception('notices_distilled_rdf_manifestation is empty.')
        return notices_distilled_rdf_manifestation

    @task()
    def insert_manifestation_to_agraph(notices_distilled_rdf_manifestation):
        agraph_ts = AllegroGraphTripleStore(host=config.ALLEGRO_HOST,
                                            user=config.AGRAPH_SUPER_USER,
                                            password=config.AGRAPH_SUPER_PASSWORD,
                                            default_repository=TDA_REPOSITORY_NAME)
        agraph_repositories = agraph_ts.list_repositories()
        if TDA_REPOSITORY_NAME not in agraph_repositories:
            agraph_ts.create_repository(repository_name=TDA_REPOSITORY_NAME)
        for notice_id, rdf_content in notices_distilled_rdf_manifestation.items():
            agraph_ts.add_data_to_repository(file_content=rdf_content, mime_type="ttl")

    insert_manifestation_to_agraph(get_manifestation_from_mongodb())


dag = load_rdf_manifestations()
