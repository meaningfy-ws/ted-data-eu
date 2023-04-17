from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import generate_nuts_level


def test_nuts_generation(real_nuts, fake_nuts):
    assert generate_nuts_level(nuts_code=fake_nuts, nuts_level=100) is None
    assert generate_nuts_level(nuts_code=real_nuts, nuts_level=0) == 'FR'
    assert generate_nuts_level(nuts_code='', nuts_level=0) is None