from datetime import datetime, date

from currency_converter import CurrencyConverter

currencyConverter = CurrencyConverter()


def convert_currency(amount: float,
                     current_currency: str,
                     exchange_date: date = datetime.today(),
                     new_currency: str = 'EUR') -> float or None:

    if not amount or not current_currency:
        return None
    if current_currency == 'EUR':
        return amount
    
    return currencyConverter.convert(amount, current_currency, new_currency, exchange_date)
