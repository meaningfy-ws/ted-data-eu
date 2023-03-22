from abc import ABC
from typing import Any

from airflow.models import BaseOperator
from dags.dags_utils import pull_dag_upstream, push_dag_downstream, get_dag_param
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC

ETL_STEP_DATA_KEY = "etl_step_data"
ETL_METADATA_DAG_CONFIG_KEY = "etl_metadata"


class ETLStepOperatorABC(BaseOperator, ABC):
    ui_color = '#e7cff6'
    ui_fgcolor = '#000000'

    def __init__(self, *args,
                 etl_pipeline: ETLPipelineABC = None,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.etl_pipeline = etl_pipeline


class ExtractStepOperator(ETLStepOperatorABC):
    """

    """

    def execute(self, context: Any):
        """

        :param context:
        :return:
        """
        dag_metadata = get_dag_param(key=ETL_METADATA_DAG_CONFIG_KEY, default_value={ETL_METADATA_DAG_CONFIG_KEY: {}})
        if self.etl_pipeline.get_pipeline_name() in dag_metadata[ETL_METADATA_DAG_CONFIG_KEY].keys():
            self.etl_pipeline.set_metadata(etl_metadata=dag_metadata[ETL_METADATA_DAG_CONFIG_KEY][self.etl_pipeline.get_pipeline_name()])
        result_data = self.etl_pipeline.extract()
        push_dag_downstream(key=ETL_STEP_DATA_KEY, value=result_data)


class TransformStepOperator(ETLStepOperatorABC):
    """

    """

    def execute(self, context: Any):
        """

        :param context:
        :return:
        """
        input_data = pull_dag_upstream(key=ETL_STEP_DATA_KEY)
        result_data = self.etl_pipeline.transform(extracted_data=input_data)
        push_dag_downstream(key=ETL_STEP_DATA_KEY, value=result_data)


class LoadStepOperator(ETLStepOperatorABC):
    """

    """

    def execute(self, context: Any):
        """

        :param context:
        :return:
        """
        input_data = pull_dag_upstream(key=ETL_STEP_DATA_KEY)
        self.etl_pipeline.load(transformed_data=input_data)
