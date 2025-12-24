import logging
from datetime import datetime
import requests
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_real_onchain_data() -> Dict[str, Any]:
    """
    当前能免费获取到的实时市场数据
    1. 恐慌与贪婪指数
    2. 比特币实时价格
    """
    data = {
        "mvrv_z_score": None,  # 付费数据暂缺
        "nupl": None,          # 付费数据暂缺
        "exchange_new_flow": None, # 付费数据暂缺
        "btc_price": 0,
        "fng_value": None,     # 恐贪数值
        "fng_class": None      # 恐贪等级
    }

    try:
        fng_response = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        if fng_response.status_code == 200:
            fng_json = fng_response.json()
            if fng_json.get("data"):
                item = fng_json['data'][0]
                data['fng_value'] = int(item['value'])
                data['fng_class'] = item['value_classification']
        else:
            logger.error(f"Failed to fetch F&G Index. Code: {fng_response.status_code}")
    
    except Exception as e:
        logger.error(f"Error fetching on-chain data: {e}")

    return data
    
def interpret_onchain_data(data: Dict[str, Any]) -> str:
    analysis_text = []

    if not data:
        return "无法获取链上数据, 请检查数据源"
    
    current_date = datetime.now().strftime("%Y-%m-%d")

    verdict_action = "观望/持有 (数据不足)"

    # 恐慌与贪婪指数分析
    fng_val = data.get('fng_value')
    fng_class = data.get('fng_class')

    if fng_val is not None:
        if fng_val < 20:
            fng_desc = "市场处于'极度恐慌'状态 控制风险"
            verdict_action = "分批买入"
        elif fng_val < 40:
            fng_desc = "市场处于'恐慌'状态 情绪偏空"
            verdict_action = "定投积累"
        elif fng_val > 75:
            fng_desc = "市场处于'极度贪婪'状态 FOMO 情绪严重 有回调风险"
            verdict_action = "停止买入"
        else:
            fng_desc = "市场情绪中性"
            verdict_action = "持有 长时间间隔买入"
        analysis_text.append(f"恐慌指数 当前值为 {fng_val} ({fng_class}) {fng_desc} ")

    # MVRV Z-Score 市场位置判断
    mvrv = data.get('mvrv_z_score', None)
    if mvrv is None:
        analysis_text.append("MVRV Z-Score 数据缺失")
    elif mvrv < 0:
        mvrv_status = "深熊底部(Deep Bear/Bottom)"
        mvrv_action = "强烈买入"
        analysis_text.append(f"MVRV Z-Score 当前值为 {mvrv} 处于 {mvrv_status} 适合强烈买入")
    elif mvrv < 1:
        mvrv_status = "低估积累区(Accumulation Zone)"
        mvrv_action = "分批定投"
        analysis_text.append(f"MVRV Z-Score 当前值为 {mvrv} 处于 {mvrv_status} 适合分批定投")
    else:
        mvrv_status = "高估区(Overvalued)"
        mvrv_action = "持有"
        analysis_text.append(f"MVRV Z-Score 当前值为 {mvrv} 处于 {mvrv_status} 持有")

    nupl = data.get('nupl', None)
    if nupl is None:
        analysis_text.append("NUPL 数据缺失")
    elif nupl < 0:
        nupl_desc = "市场处于Capitulation阶段"
        analysis_text.append(f"NUPL 情绪指标 当前值为 {nupl} {nupl_desc}")
    elif nupl < 0.25:
        nupl_desc = "市场处于'恐惧/希望'阶段 抛压逐渐衰竭"
        analysis_text.append(f"NUPL 情绪指标 当前值为 {nupl} {nupl_desc}")
    else:
        nupl_desc = "市场处于盈利状态 可能面临获利盘回吐"
        analysis_text.append(f"NUPL 情绪指标 当前值为 {nupl} {nupl_desc}")

    # 交易所流量
    flow = data.get('exchange_new_flow', None)
    if flow is None:
        analysis_text.append("交易所净流量 数据缺失")
    elif flow < -1000:
        flow_desc = "检测到大量比特币从交易所流出到冷钱包 巨鲸正在囤币 供应冲击可能导致后续价格上涨"
        analysis_text.append(f"交易所净流量 过去24小时净流向为 {flow} BTC {flow_desc}")
    elif flow > 1000:
        flow_desc = "大量比特币流入交易所 可能存在潜在的砸盘风险"
        analysis_text.append(f"交易所净流量 过去24小时净流向为 {flow} BTC {flow_desc}")
    else:
        flow_desc = "交易所流量相对平稳 供需平衡"
        analysis_text.append(f"交易所净流量 过去24小时净流向为 {flow} BTC {flow_desc}")
    
    full_report = f"""
    [BTC On-Chain Analysis Report - {current_date}]
    Fear & Greed Index: {fng_val} ({fng_class})

    Summary:
    {chr(10).join(["- " + line for line in analysis_text])}

    Investment Verdict: 
    基于链上数据 当前市场处于 {verdict_action} 阶段
    """
    return full_report

def generate_btc_onchain_report():
    logger.info("Starting market data fetch...")
    data = fetch_real_onchain_data()
    print(data)
    report = interpret_onchain_data(data)
    logger.info(report)
    return report