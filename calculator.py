from decimal import Decimal
from models import AssetSnapshot, AssetResults
from config import RISK_WEIGHTS
from utils import get_usd_value, get_gold_value, get_value

def calculate_asset_metrics(data: AssetSnapshot, rates: dict, btc_risk_score: Decimal) -> AssetResults:
    cny_total = get_value(data.retirement_funds_cny) + get_value(data.funds_cny) + get_value(data.savings_cny) + get_value(data.housing_fund_cny)
    eur_total = get_value(data.savings_eur) + get_value(data.funds_eur)
    sgd_total = get_value(data.savings_sgd) + get_value(data.funds_sgd)
    hkd_total = get_value(data.savings_hkd) + get_value(data.funds_hkd)

    values_in_usd = {
        'gold': get_gold_value(get_value(data.gold_g), get_value(data.gold_oz), rates['XAU']),
        'cny': get_usd_value(cny_total, rates['CNY']),
        'gbp': get_usd_value(get_value(data.deposit_gbp), rates['GBP']),
        'eur': get_usd_value(eur_total, rates['EUR']),
        'sgd': get_usd_value(sgd_total, rates['SGD']),
        'hkd': get_usd_value(hkd_total, rates['HKD']),
        
        'btc': get_usd_value(get_value(data.btc), rates['BTC']) + get_value(data.btc_stock_usd),
        
        'usd': get_value(data.savings_usd) + get_value(data.stock_usd)
    }

    savings_in_usd = {
        'cny': get_usd_value(get_value(data.savings_cny), rates['CNY']),
        'eur': get_usd_value(get_value(data.savings_eur), rates['EUR']),
        'sgd': get_usd_value(get_value(data.savings_sgd), rates['SGD']),
        'hkd': get_usd_value(get_value(data.savings_hkd), rates['HKD']),
        'usd': get_value(data.savings_usd)
    }

    total_assets_usd = sum(values_in_usd.values())
    total_savings_usd = sum(savings_in_usd.values())

    if total_assets_usd == Decimal('0'):
        available_liquidity_ratio = Decimal('0')
        gold_ratio = Decimal('0')
        btc_ratio = Decimal('0')
    else:
        available_liquidity_ratio = total_savings_usd / total_assets_usd * 100
        gold_ratio = values_in_usd['gold'] / total_assets_usd * 100 
        total_btc_usd = values_in_usd['btc']
        btc_ratio = total_btc_usd / total_assets_usd * 100

    risk_weighted_sum = Decimal('0')
    # 1. 现金类(储蓄 + 存款)
    cash_val = (
        get_usd_value(get_value(data.savings_cny), rates['CNY']) +
        get_usd_value(get_value(data.savings_eur), rates['EUR']) +
        get_usd_value(get_value(data.savings_sgd), rates['SGD']) +
        get_usd_value(get_value(data.savings_hkd), rates['HKD']) +
        get_usd_value(get_value(data.deposit_gbp), rates['GBP']) +
        get_value(data.savings_usd)
    )

    risk_weighted_sum += cash_val * RISK_WEIGHTS['savings']
    # 2. 政策性资产(公积金 + 养老金)
    policy_val = get_usd_value(get_value(data.housing_fund_cny) + get_value(data.retirement_funds_cny), rates['CNY'])
    risk_weighted_sum += policy_val * RISK_WEIGHTS['housing']

    # 3. 基金类(混合型基金)
    funds_val = (
        get_usd_value(get_value(data.funds_cny), rates['CNY']) +
        get_usd_value(get_value(data.funds_eur), rates['EUR']) +
        get_usd_value(get_value(data.funds_hkd), rates['HKD']) +
        get_usd_value(get_value(data.funds_sgd), rates['SGD'])
    )
    risk_weighted_sum += funds_val * RISK_WEIGHTS['funds_mixed']

    # 4. 黄金
    risk_weighted_sum += values_in_usd['gold'] * RISK_WEIGHTS['gold']

    # 5. 股票
    risk_weighted_sum += get_value(data.stock_usd) * RISK_WEIGHTS['stock']

    # 6. 比特币(直接持有 + 相关股票持有)
    btc_val = values_in_usd['btc']
    risk_weighted_sum += btc_val * btc_risk_score

    # 计算最终加权分数
    weighted_risk_score = Decimal('0')
    if total_assets_usd > 0:
        weighted_risk_score = risk_weighted_sum / total_assets_usd

    # 计算投机比例
    speculative_assets = Decimal('0')
    speculative_assets += values_in_usd['gold'] * RISK_WEIGHTS['gold'] / Decimal('10')
    speculative_assets += get_value(data.stock_usd) * RISK_WEIGHTS['stock'] / Decimal('10')
    speculative_assets += btc_val * RISK_WEIGHTS['btc'] / Decimal('10')
    values_in_usd['gold'] + get_value(data.stock_usd) + btc_val
    if total_assets_usd > 0:
        speculative_ratio = (speculative_assets / total_assets_usd) * 100

    results = AssetResults(
        total_assets_usd=total_assets_usd,
        total_savings_usd=total_savings_usd,
        available_liquidity_ratio=available_liquidity_ratio,
        gold_ratio=gold_ratio,
        btc_ratio=btc_ratio,

        weighted_risk_score=weighted_risk_score,
        speculative_ratio=speculative_ratio
    )
    return results