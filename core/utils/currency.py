from decimal import Decimal, InvalidOperation
from core.models import Currency

# Static conversion rates
CURRENCY_RATES = {
    'KES': Decimal("1"),        # base currency
    'USD': Decimal("0.0071"),
    'EUR': Decimal("0.0065"),
    'GBP': Decimal("0.0057"),
    'BTC': Decimal("0.00000018"),
    'ETH': Decimal("0.0000028"),
    'ZAR': Decimal("0.12"),
    'TZS': Decimal("18.4"),
    'UGX': Decimal("26.3")
}

CURRENCY_SYMBOLS = {
    'KES': 'KSh',
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'BTC': '₿',
    'ETH': 'Ξ',
    'ZAR': 'R',
    'TZS': 'TSh',
    'UGX': 'USh'
}
def convert_amount(amount, to_currency_code='KES', reverse=False):
    """
    Convert a Decimal amount between KES (base) and target currency.
    - reverse=False: base → target
    - reverse=True: target → base
    """
    if not amount:
        return Decimal("0.00")
    
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    rate = CURRENCY_RATES.get(to_currency_code, Decimal("1"))
    
    try:
        if reverse:
            # Convert target → base
            return (amount / rate).quantize(Decimal("0.01"))
        else:
            # Convert base → target
            return (amount * rate).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def get_currency_symbol(code):
    """Return the symbol for a currency code."""
    return CURRENCY_SYMBOLS.get(code, '')
