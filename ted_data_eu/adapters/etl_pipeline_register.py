from ted_data_eu.adapters.etl_pipeline_abc import ETLPipelineABC


class ETLPipelineRegister:
    """
        This class is used to create a registry of ETL pipelines.
    """

    def __init__(self):
        self.pipelines_register = {}

    def register(self, etl_pipeline_name: str, etl_pipeline: ETLPipelineABC):
        """
            This method registers a new ETL pipeline in the registry.
        :param etl_pipeline_name:
        :param etl_pipeline:
        :return:
        """
        self.pipelines_register[etl_pipeline_name] = etl_pipeline

    def unregister(self, etl_pipeline_name: str):
        """
           This method deletes an ETL pipeline from the registry.
        :param etl_pipeline_name:
        :return:
        """
        self.pipelines_register.pop(etl_pipeline_name)
