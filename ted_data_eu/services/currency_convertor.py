import datetime
import logging
from datetime import date
from typing import Tuple

from currency_converter import CurrencyConverter, RateNotFoundError

cur_converter = CurrencyConverter()


def convert_currency(amount: float, currency: str, new_currency: str, date: date = None) -> float:
    """
        Converts the currency and returns the converted amount or 0.0 if the conversion was not possible
    """
    if currency == new_currency:
        return amount
    try:
        return cur_converter.convert(amount=amount, currency=currency, new_currency=new_currency, date=date)
    except (RateNotFoundError, ValueError) as e:
        logging.warning(str(e) + ". 0.0 value will be used")

    return 0.0

def convert_currency_last_date(amount: float, currency: str, new_currency: str) -> Tuple[float, datetime.date]:
    """
        Converts the currency and returns the last available date for which the conversion was made
    """
    first_date, last_date = cur_converter.bounds[currency]
    try:
        converted_currency = cur_converter.convert(amount=amount, currency=currency, new_currency=new_currency)
        return converted_currency, last_date
    except (RateNotFoundError, ValueError) as e:
        logging.warning(str(e) + ". 0.0 value will be used")

    return 0.0, last_date


def get_last_available_date_for_currency(currency: str) -> date:
    """
        Returns the last available date for which the conversion was made
    """
    first_date, last_date = cur_converter.bounds[currency]
    return last_date