from datetime import datetime

from ted_data_eu.services.currency_convertor import convert_currency


def test_convert_currency():
    fake_date = datetime.strptime("19760101", "%Y%m%d")
    sample_amount = 100
    sample_currency = 'EUR'
    sample_currency2 = 'BGN'
    fake_currency = 'XYZ'
    real_date = datetime.strptime("20200115", "%Y%m%d")

    assert convert_currency(sample_amount, sample_currency, sample_currency2, fake_date) is None
    assert convert_currency(sample_amount, sample_currency, fake_currency) is None
    assert convert_currency(sample_amount, sample_currency, sample_currency2, real_date) is not None
