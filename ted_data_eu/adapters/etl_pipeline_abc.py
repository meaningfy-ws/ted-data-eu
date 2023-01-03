import abc
from typing import Dict


class ETLPipelineABC(abc.ABC):
    """
        This class represents a template for an ETL pipeline.
    """
    @abc.abstractmethod
    def extract(self) -> Dict:
        """
           This method extracts the data and passes it to the transformation method.
        :return:
        """

    @abc.abstractmethod
    def transform(self, extracted_data: Dict) -> Dict:
        """
           This method transforms the data and passes it to the load method.
        :param extracted_data:
        :return:
        """

    @abc.abstractmethod
    def load(self, transformed_data: Dict):
        """
            This method stores the transformed data.
        :param transformed_data:
        :return:
        """




