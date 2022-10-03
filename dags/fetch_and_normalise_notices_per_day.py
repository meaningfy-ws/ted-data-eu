from dags import DEFAULT_DAG_ARGUMENTS
from airflow.decorators import dag, task

from ted_sws.data_manager.adapters.notice_repository import NoticeRepository
from ted_sws.notice_fetcher.services.notice_fetcher import NoticeFetcher
from ted_sws.notice_fetcher.adapters.ted_api import TedAPIAdapter, TedRequestAPI


@dag(default_args=DEFAULT_DAG_ARGUMENTS,
     schedule_interval=None,
     tags=['fetch', 'fuseki'])
def fetch_and_normalise_notices_per_day():
    @task()
    def fetch_notices_ids():
        pass

    @task()
    def fetch_and_normalise_notices_and_store_to_mongo():
        pass

    @task()
    def load_notices_from_mongo_to_fuseki():
        pass

    pass


dag = fetch_and_normalise_notices_per_day()
