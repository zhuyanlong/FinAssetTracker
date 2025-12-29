import logging

from decimal import Decimal
from models import AssetSnapshot, AssetResults
from config import ASSET_CONFIG
from utils import get_usd_value

def calculate_asset_metrics(data: AssetSnapshot, rates: dict, btc_risk_score: Decimal) -> AssetResults:
    total_assets_usd = Decimal('0')
    total_savings_usd = Decimal('0')

    gold_val_usd = Decimal('0')
    btc_val_usd = Decimal('0')
    currency_exposure = {} # 货币敞口计算

    asset_dict = data.model_dump()

    for field, amount in asset_dict.items():
        if amount is None or field == 'id' or field == 'snapshot_date':
            continue

        amount_dec = Decimal(str(amount))
        if amount_dec == 0: 
            continue

        config = ASSET_CONFIG.get(field)

        if not config:
            continue

        currency =  config['currency']
        is_liquid_flag = config['liquid']
        unit_scale = Decimal(str(config.get('unit_scale', 1.0)))

        rate = rates.get(currency, Decimal('0'))
        usd_value = get_usd_value(amount_dec, unit_scale, rate)

        total_assets_usd += usd_value

        if is_liquid_flag:
            total_savings_usd += usd_value

        if 'gold' in field:
            gold_val_usd += usd_value

        if 'btc' in field:
            btc_val_usd += usd_value

        currency_exposure[currency] = currency_exposure.get(currency, Decimal('0')) + usd_value
    logging.info(f"total_assets_usd is {total_assets_usd}")
    available_liquidity_ratio = Decimal('0')
    if total_assets_usd > 0:
        available_liquidity_ratio = (total_savings_usd / total_assets_usd) * 100

    gold_ratio = Decimal('0')
    if total_assets_usd > 0:
        gold_ratio = (gold_val_usd / total_assets_usd) * 100

    btc_ratio = Decimal('0')
    if total_assets_usd > 0:
        btc_ratio = (btc_val_usd / total_assets_usd) * 100

    weighted_risk_sum = Decimal('0')
    speculative_sum = Decimal('0')

    for field, amount in asset_dict.items():
        if field not in ASSET_CONFIG or amount == 0:
            continue

        config = ASSET_CONFIG[field]
        amount_dec = Decimal(str(amount))

        rate = rates.get(config['currency'], Decimal('0'))
        unit_scale = Decimal(str(config.get('unit_scale', 1.0)))
        val_usd = get_usd_value(amount_dec, unit_scale, rate)

        risk_score = Decimal(config['risk'])
        if 'btc' in field and btc_risk_score > 0:
            risk_score = btc_risk_score

        weighted_risk_sum += val_usd * risk_score

        # 投机资产
        if risk_score > 5:
            speculative_sum += val_usd

    logging.info(f"weighted_risk_sum is {weighted_risk_sum}, speculative_sum is {speculative_sum}")
    weighted_risk_score = Decimal('0')
    speculative_ratio = Decimal('0')

    if total_assets_usd > 0:
        weighted_risk_score = weighted_risk_sum / total_assets_usd
        speculative_ratio = (speculative_sum / total_assets_usd) * 100

    currency_dist_final = {}
    if total_assets_usd > 0:
        for curr, val in currency_exposure.items():
            pct = (val / total_assets_usd) * 100
            if pct > 0.01:
                currency_dist_final[curr] = float(round(pct, 2))
    return AssetResults(
        total_assets_usd=total_assets_usd,
        total_savings_usd=total_savings_usd,
        available_liquidity_ratio=available_liquidity_ratio,
        gold_ratio=gold_ratio,
        btc_ratio=btc_ratio,
        weighted_risk_score=weighted_risk_score,
        speculative_ratio=speculative_ratio,
        currency_distribution=currency_dist_final
    )