from ted_data_eu.adapters.etl_pipeline_register import ETLPipelineRegister
from ted_data_eu.services.etl_pipelines.dummy_etl_pipeline import DummyETLPipeline, TestETLPipeline

etl_pipelines_register = ETLPipelineRegister()

etl_pipelines_register.register(etl_pipeline_name="Test ETL 1 pipeline", etl_pipeline=DummyETLPipeline())
etl_pipelines_register.register(etl_pipeline_name="Test ETL 2 pipeline", etl_pipeline=TestETLPipeline())
