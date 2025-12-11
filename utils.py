from decimal import Decimal
from config import GRAMS_TO_OUNCES_TROY

def get_usd_value(money: Decimal, rate: Decimal):
    return (Decimal('1') / rate) * money if rate != Decimal('0') else Decimal('0')

def get_gold_value(grams: Decimal, oz: Decimal, rate: Decimal):
    ounces = grams * GRAMS_TO_OUNCES_TROY + oz
    return ounces * (Decimal('1') / rate) if rate != Decimal('0') else Decimal('0')

def get_value(field) -> Decimal: 
    if field is None or str(field) == "":
        return Decimal('0')
    return Decimal(str(field))