from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import generate_nuts_code_by_level

def test_nuts_generation(real_nuts, fake_nuts):
    assert generate_nuts_code_by_level(nuts_code=fake_nuts, nuts_level=100) is None
    assert generate_nuts_code_by_level(nuts_code=real_nuts, nuts_level=0) == 'FR'
    assert generate_nuts_code_by_level(nuts_code='', nuts_level=0) is None

    assert generate_nuts_code_by_level(nuts_code=real_nuts, nuts_level=1) == 'FRK'
    assert generate_nuts_code_by_level(nuts_code=real_nuts, nuts_level=2) == 'FRK2'
    assert generate_nuts_code_by_level(nuts_code=real_nuts, nuts_level=3) == 'FRK26'
    assert generate_nuts_code_by_level(nuts_code=real_nuts, nuts_level=4) is None
