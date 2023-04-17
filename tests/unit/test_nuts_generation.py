from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import generate_nuts_lvl


def test_nuts_generation(real_nuts, fake_nuts):
    assert generate_nuts_lvl(nuts_code=fake_nuts, lvl=100) is None
    assert generate_nuts_lvl(nuts_code=real_nuts, lvl=0) == 'FR'
    assert generate_nuts_lvl(nuts_code='', lvl=0) is None