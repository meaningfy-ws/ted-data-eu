from string import Template

from ted_data_eu import config
from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import TedDataETLPipeline, \
    generate_sparql_filter_by_date_range
from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import generate_dates_by_date_range


def test_generate_sparql_filter_by_date_range():
    test_result = generate_sparql_filter_by_date_range("20151208", "20151223")
    assert len(test_result.split(" ")) == 16

def test_date_range_generator():
    test_range = generate_dates_by_date_range("20151208", "20151223")
    assert len(test_range) == 16

def test_etl_pipeline():
    multiple_dates_metadata = {"start_date": "20180314", "end_date": "20180314"}
    single_date_metadata = {}

    ted_pipeline = TedDataETLPipeline()
    ted_pipeline.set_metadata(multiple_dates_metadata)
    data = ted_pipeline.extract()
    data = ted_pipeline.transform(data)
    ted_pipeline.load(data)
    print(data['data'].head().to_string())

