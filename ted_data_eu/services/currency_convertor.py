import logging
from datetime import date

from currency_converter import CurrencyConverter, RateNotFoundError

cur_converter = CurrencyConverter()


def convert_currency(amount: float, currency: str, new_currency: str, date: date = None) -> float:
    try:
        return cur_converter.convert(amount=amount, currency=currency, new_currency=new_currency, date=date)
    except (RateNotFoundError, ValueError) as e:
        logging.warning(str(e) + ". None value will be used")

    return 0.0
