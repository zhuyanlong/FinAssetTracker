from models import AssetSnapshot
from decimal import Decimal

def demo_asset_snapshot() -> AssetSnapshot:
    return AssetSnapshot(
        gold_g=Decimal("100"),
        gold_oz=Decimal("0.1"),
        btc=Decimal("0.1"),
        btc_stock_usd=Decimal("100"),
        Deposit_gbp=Decimal("10"),
        retirement_funds_cny=Decimal("1000"),
        savings_cny=Decimal("100"),
        funds_cny=Decimal("100"),
        housing_fund_cny=Decimal("100"),
        funds_sgd=Decimal("100"),
        savings_hkd=Decimal("100"),
        savings_eur=Decimal("100"),
        savings_usd=Decimal('10000'),
        stock_usd=Decimal("100")
    )