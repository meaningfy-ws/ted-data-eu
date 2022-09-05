from airflow.decorators import dag, task
from datetime import datetime, timedelta

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

    @task()
    def get_manifestation_from_mongodb():
        pass

    @task()
    def insert_manifestation_to_agraph():
        pass

    get_manifestation_from_mongodb() >> insert_manifestation_to_agraph()

dag = load_rdf_manifestations()