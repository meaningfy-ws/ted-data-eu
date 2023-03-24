from airflow.decorators import dag, task

from dags import DEFAULT_DAG_ARGUMENTS
from ted_data_eu.adapters.storage import ElasticStorage

TED_DATA_ETL_PIPELINE_NAME = "ted_data"

@dag(default_args=DEFAULT_DAG_ARGUMENTS,
     schedule_interval=None,
     tags=['dummy'])
def dummy_funky_dag():
    @task
    def test():
        """

        :return:
        """
        elastic_storage = ElasticStorage(elastic_index=TED_DATA_ETL_PIPELINE_NAME)


    test()


dag = dummy_funky_dag()
