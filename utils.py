from decimal import Decimal
from config import ASSET_CONFIG

def get_usd_value(money: Decimal, unit_scale: Decimal, rate: Decimal):
    if rate != Decimal('0'):
        return (Decimal('1') / rate) * money * unit_scale 
    else:
        return Decimal('0')

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