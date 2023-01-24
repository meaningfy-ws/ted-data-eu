from datetime import date

from ted_data_eu.services.currency_convertor import convert_currency


def test_convert_currency():
    assert convert_currency(None, None) is None
    assert convert_currency(None, 'RON') is None
    assert convert_currency(10.0, 'RON', date(2021, 7, 5)) is not None
    assert convert_currency(100.0, 'USD', date(2100, 10, 20)) is None
    assert convert_currency(0.0, 'RON', date(2021, 7, 5)) == 0.0
