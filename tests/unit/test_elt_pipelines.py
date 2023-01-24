from ted_data_eu.services.etl_pipelines.potential_customers_etl_pipeline import PotentialCustomersETLPipeline


def test_potential_customers_etl():
    etl_pipeline = PotentialCustomersETLPipeline(query_limit=1000)
    extracted_data = etl_pipeline.extract()
    assert 'data' in extracted_data.keys()
    assert extracted_data['data'] is not None
    transformed_data = etl_pipeline.transform(extracted_data)
    assert 'data' in transformed_data.keys()
    assert transformed_data['data'] is not None
    transformed_data_df = transformed_data['data']
    df_columns = transformed_data_df.columns
    assert 'CustomerEmail' in df_columns
    assert 'CustomerName' in df_columns
    assert 'ContractTitle' in df_columns
    assert 'LotCPV' in df_columns
    assert 'ContractConclusionDate' in df_columns
    assert 'Currency' in df_columns
    assert 'LotCPV' in df_columns
