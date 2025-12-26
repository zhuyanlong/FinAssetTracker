from decimal import Decimal
from config import GRAMS_TO_OUNCES_TROY, ASSET_CONFIG

def get_usd_value(money: Decimal, rate: Decimal):
    return (Decimal('1') / rate) * money if rate != Decimal('0') else Decimal('0')

def get_gold_value(grams: Decimal, oz: Decimal, rate: Decimal):
    ounces = grams * GRAMS_TO_OUNCES_TROY + oz
    return ounces * (Decimal('1') / rate) if rate != Decimal('0') else Decimal('0')

def get_value(field) -> Decimal: 
    if field is None or str(field) == "":
        return Decimal('0')
    return Decimal(str(field))

def get_asset_info(field_name: str):
    return ASSET_CONFIG.get(field_name, {
        "currency": "USD", "risk": 5, "liquid": False, "unit_scale": 1.0, "name": field_name
    })

def get_currency_code(field_name: str) -> str:
    return get_asset_info(field_name)['currency']

def get_unit_scale(field_name: str) -> Decimal:
    return Decimal(str(get_asset_info(field_name)['unit_scale']))

def is_liquid(field_name: str) -> bool:
    return get_asset_info(field_name)['liquid'] 