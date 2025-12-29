import logging

from decimal import Decimal
from typing import Dict, List
from models import AssetResults, SmartSuggestion

def evaluate_fx_status(
    currency: str,
    current_rate: Decimal,
    ref_rates: dict[str, Decimal],
    band: Decimal = Decimal("0.05")
) -> str:
    """
    判断非美元货币相对于美元的估值状态
    """
    if currency == "USD" or currency == "BTC" or currency == "GOLD":
        return "N/A"
    
    ref_rate = ref_rates.get(currency)
    if not ref_rate:
        return "N/A"
    
    if current_rate >= ref_rate * (1 + band):
        return "CHEAP"
    elif current_rate <= ref_rate * (1 - band):
        return "EXPENSIVE"
    else:
        return "FAIR"

def calculate_strategic_rebalancing(
    results: AssetResults,
    target_map: Dict[str, Decimal],
    threshold: Decimal,
    current_rates: Dict[str, Decimal],
    fx_refs: Dict[str, Decimal]
) -> List[SmartSuggestion]:
    
    suggestions = []
    total_assets = results.total_assets_usd
    if total_assets == 0:
        return []
    
    current_dist = results.currency_distribution
    mapped_current = current_dist.copy()
    actual_other = Decimal(0)
    for k, v in current_dist.items():
        if k not in target_map:
            actual_other += v

    logging.warning(f"actual_other is {actual_other}")

    if "OTHER" in target_map:
        mapped_current["OTHER"] = mapped_current.get("OTHER", Decimal(0)) + actual_other

    for asset, target_pct in target_map.items():
        current_pct = mapped_current.get(asset, Decimal(0))

        drift = current_pct - target_pct
        adjustment_usd = abs(total_assets * (drift / 100))

        fx_status = evaluate_fx_status(asset, current_rates.get(asset, Decimal(0)), fx_refs)

        action = "WAIT"
        reason = "Within threshold"

        # 超配
        if drift > threshold:
            if fx_status == "EXPENSIVE":
                action = "STRONG SELL"
                reason = f"超配 {drift:.1f}% 且汇率高估(贵), 建议止盈"
            elif fx_status == "CHEAP":
                action = "HOLD"
                reason = f"虽超配 {drift:.1f}% 但汇率低估(便宜), 暂缓卖出"
            else:
                action = "SELL"
                reason = f"超配 {drift:.1f}% 建议再平衡"

        # 低配
        elif drift < -threshold:
            if fx_status == "CHEAP":
                action = "STRONG BUY"
                reason = f"低配 {abs(drift):.1f}% 且汇率低, 建议买入"
            elif fx_status == "EXPENSIVE":
                action = "HOLD"
                reason = f"虽低配 {abs(drift):.1f}% 但汇率过高, 暂缓买入"
            else:
                action = "BUY"
                reason = f"低配 {abs(drift):.1f}% 建议补仓"

        else:
            if fx_status == "EXPENSIVE" and drift > 0:
                action = "TRIM"
                reason = "仓位正常但汇率高"
            elif fx_status == "CHEAP" and drift < 0:
                action = "ADD"
                reason = "仓位正常但汇率便宜"

        if action != "WAIT":
            suggestions.append(SmartSuggestion(
                asset_class=asset,
                current_pct=current_pct,
                target_pct=target_pct,
                drift=drift,
                fx_status=fx_status,
                action=action,
                amount_usd=adjustment_usd,
                reason=reason
            ))
    return suggestions
