import logging
from typing import Optional

from currency_converter import CurrencyConverter, RateNotFoundError
from datetime import date

cur_converter = CurrencyConverter()


def convert_currency(amount: float, currency: str, new_currency: str, date: date = None) -> Optional[float]:
    try:
        return cur_converter.convert(amount=amount, currency=currency, new_currency=new_currency, date=date)
    except (RateNotFoundError, ValueError) as e:
        logging.warning(str(e) + ". None value will be used")

    return None
