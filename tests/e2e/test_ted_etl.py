
def test_etl_pipeline(ted_data_etl_pipeline, etl_pipeline_config, wrong_etl_pipeline_config):
    ted_data_etl_pipeline.set_metadata(etl_pipeline_config)
    data = ted_data_etl_pipeline.extract()
    data = ted_data_etl_pipeline.transform(data)
    ted_data_etl_pipeline.load(data)

    ted_data_etl_pipeline.set_metadata(wrong_etl_pipeline_config)
    data = ted_data_etl_pipeline.extract()
    data = ted_data_etl_pipeline.transform(data)
    ted_data_etl_pipeline.load(data)
