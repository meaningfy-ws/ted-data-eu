from abc import ABC
from typing import Any
import tempfile
from airflow.models import BaseOperator
from dags.dags_utils import pull_dag_upstream, push_dag_downstream, get_dag_param
from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC

ETL_STEP_DATA_KEY = "etl_step_data"
ETL_METADATA_DAG_CONFIG_KEY = "etl_metadata"


def store_dict_as_pickle_in_tmp_file(data: dict) -> pathlib.Path:
    """
        Stores a dictionary as pickle in a temporary file
    :param data: Dictionary to be stored
    :return: Path to the temporary file
    """
    with tempfile.NamedTemporaryFile(suffix=".pickle", delete=False) as tmp_file:
        pickle.dump(data, tmp_file)
        return pathlib.Path(tmp_file.name)


def load_dict_from_pickle_file(pickle_file_path: pathlib.Path) -> dict:
    """
        Loads a dictionary from a pickle file
    :param pickle_file_path: Path to the pickle file
    :return: Dictionary
    """
    with open(pickle_file_path, "rb") as pickle_file:
        return pickle.load(pickle_file)


def delete_pickle_tmp_file(pickle_file_path: pathlib.Path):
    """
        Deletes a pickle file
    :param pickle_file_path: Path to the pickle file
    :return:
    """
    if pickle_file_path.exists():
        pickle_file_path.unlink()


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
        tmp_path = store_dict_as_pickle_in_tmp_file(data=result_data)
        push_dag_downstream(key=ETL_STEP_DATA_KEY, value=tmp_path)


class TransformStepOperator(ETLStepOperatorABC):
    """

    """

    def execute(self, context: Any):
        """

        :param context:
        :return:
        """
        tmp_path = pull_dag_upstream(key=ETL_STEP_DATA_KEY)
        input_data = load_dict_from_pickle_file(pickle_file_path=tmp_path)
        result_data = self.etl_pipeline.transform(extracted_data=input_data)
        delete_pickle_tmp_file(pickle_file_path=tmp_path)
        tmp_path = store_dict_as_pickle_in_tmp_file(data=result_data)
        push_dag_downstream(key=ETL_STEP_DATA_KEY, value=tmp_path)


class LoadStepOperator(ETLStepOperatorABC):
    """

    """

    def execute(self, context: Any):
        """

        :param context:
        :return:
        """
        tmp_path = pull_dag_upstream(key=ETL_STEP_DATA_KEY)
        input_data = load_dict_from_pickle_file(pickle_file_path=tmp_path)
        self.etl_pipeline.load(transformed_data=input_data)
        delete_pickle_tmp_file(pickle_file_path=tmp_path)
