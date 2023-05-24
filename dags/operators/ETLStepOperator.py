from abc import ABC
from typing import Any
import pickle
import lzma
from airflow.models import BaseOperator
from dags.dags_utils import pull_dag_upstream, push_dag_downstream, get_dag_param
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC

ETL_STEP_DATA_KEY = "etl_step_data"
ETL_METADATA_DAG_CONFIG_KEY = "etl_metadata"


def compress_dict_data_with_lzma(data: dict) -> bytes:
    """
        Compresses a dictionary with lzma
    :param data: Dictionary to be compressed
    :return: Compressed dictionary
    """
    return lzma.compress(pickle.dumps(data), preset=lzma.PRESET_DEFAULT)


def uncompress_dict_data_with_lzma(data: bytes) -> dict:
    """
        Uncompresses a dictionary with lzma
    :param data: Compressed dictionary
    :return: Uncompressed dictionary
    """
    return pickle.loads(lzma.decompress(data))


class ETLStepOperatorABC(BaseOperator, ABC):
    """
        This class represents a template for an ETL step operator.
    """
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
        etl_dag_metadata = get_dag_param(key=ETL_METADATA_DAG_CONFIG_KEY, default_value={})
        if self.etl_pipeline.get_pipeline_name() in etl_dag_metadata.keys():
            self.etl_pipeline.set_metadata(etl_metadata=etl_dag_metadata[self.etl_pipeline.get_pipeline_name()])
        result_data = self.etl_pipeline.extract()
        compressed_result_data = compress_dict_data_with_lzma(data=result_data)
        push_dag_downstream(key=ETL_STEP_DATA_KEY, value=compressed_result_data)


class TransformStepOperator(ETLStepOperatorABC):
    """

    """

    def execute(self, context: Any):
        """

        :param context:
        :return:
        """
        compressed_input_data = pull_dag_upstream(key=ETL_STEP_DATA_KEY)
        input_data = uncompress_dict_data_with_lzma(data=compressed_input_data)
        result_data = self.etl_pipeline.transform(extracted_data=input_data)
        compressed_result_data = compress_dict_data_with_lzma(data=result_data)
        push_dag_downstream(key=ETL_STEP_DATA_KEY, value=compressed_result_data)


class LoadStepOperator(ETLStepOperatorABC):
    """

    """

    def execute(self, context: Any):
        """

        :param context:
        :return:
        """
        compressed_input_data = pull_dag_upstream(key=ETL_STEP_DATA_KEY)
        input_data = uncompress_dict_data_with_lzma(data=compressed_input_data)
        self.etl_pipeline.load(transformed_data=input_data)
