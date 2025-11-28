from pydantic import BaseModel
from decimal import Decimal

class AssetData(BaseModel):
    gold_g: Decimal = Decimal('0')
    gold_oz: Decimal = Decimal('0')

    retirement_funds_cny: Decimal = Decimal('0')
    savings_cny: Decimal = Decimal('0')
    funds_cny: Decimal = Decimal('0')
    housing_fund_cny: Decimal = Decimal('0')

    funds_sgd: Decimal = Decimal('0')
    savinds_sgd: Decimal = Decimal('0')

    funds_eur: Decimal = Decimal('0')
    savings_eur: Decimal = Decimal('0')

    funds_hkd: Decimal = Decimal('0')
    savings_hkd: Decimal = Decimal('0')

    btc: Decimal = Decimal('0')
    btc_stock_usd: Decimal = Decimal('0')

    funds_eur : Decimal = Decimal('0')
    savings_eur: Decimal = Decimal('0')

    savings_usd: Decimal = Decimal('0')
    stock_usd: Decimal = Decimal('0')
    
