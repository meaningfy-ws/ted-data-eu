from ted_data_eu.services.etl_pipelines.postgres_etl_pipeline import generate_link_to_notice
from ted_data_eu.services.etl_pipelines.ted_data_etl_pipeline import generate_nuts_code_by_level


def test_nuts_generation(real_nuts, fake_nuts):
    assert generate_nuts_code_by_level(nuts_code=fake_nuts, nuts_level=100) is None
    assert generate_nuts_code_by_level(nuts_code=real_nuts, nuts_level=0) == 'FR'
    assert generate_nuts_code_by_level(nuts_code='', nuts_level=0) is None

    assert generate_nuts_code_by_level(nuts_code=real_nuts, nuts_level=1) == 'FRK'
    assert generate_nuts_code_by_level(nuts_code=real_nuts, nuts_level=2) == 'FRK2'
    assert generate_nuts_code_by_level(nuts_code=real_nuts, nuts_level=3) == 'FRK26'
    assert generate_nuts_code_by_level(nuts_code=real_nuts, nuts_level=4) is None


def test_nuts_processor(real_nuts, fake_nuts, nuts_processor):
    assert nuts_processor.nuts_exists(nuts_code=real_nuts) is True
    assert nuts_processor.nuts_exists(nuts_code=fake_nuts) is False

    assert nuts_processor.get_nuts_label_by_code(nuts_code=real_nuts) == 'Rhône'
    assert nuts_processor.get_nuts_label_by_code(nuts_code=fake_nuts) is None

    assert nuts_processor.get_nuts_level_by_code(nuts_code=real_nuts) == 3
    assert nuts_processor.get_nuts_level_by_code(nuts_code=fake_nuts) is None


def test_notice_link_generation():
    assert generate_link_to_notice(
        "epd:id_2015-S-250-456405_Notice") == "https://ted.europa.eu/udl?uri=TED:NOTICE:456405-2015:TEXT:EN:HTML"
    assert generate_link_to_notice(None) is None
    assert generate_link_to_notice("epdd_2015-S-25405_Notice") is None
    assert generate_link_to_notice(
        "epd:id_2022-S-250-453405_Notice") == "https://ted.europa.eu/udl?uri=TED:NOTICE:453405-2022:TEXT:EN:HTML"
