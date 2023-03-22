

def test_etl_pipeline(ted_data_etl_pipeline):
    multiple_dates_metadata = {"start_date": "20180314", "end_date": "20180314"}


    ted_data_etl_pipeline.set_metadata(multiple_dates_metadata)
    data = ted_data_etl_pipeline.extract()
    data = ted_data_etl_pipeline.transform(data)
    ted_data_etl_pipeline.load(data)
    #print(data['data'].head().to_string())
