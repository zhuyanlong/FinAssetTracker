import requests
import pandas as pd
import numpy as np
import redis
import logging

from decimal import Decimal
from config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    BTC_RISK_KEY,
    RISK_WEIGHTS
)

RISK_REDIS_CLIENT = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

def update_and_cache_btc_risk() -> Decimal:
    """
    获取 BTC 历史数据，计算风险系数，并将结果存储到 Redis。
    """
    df = fetch_btc_history_kraken()
    if df is None:
        risk_score = RISK_WEIGHTS['btc']
    else:
        close_prices = df['close']
        risk_score = calculate_btc_risk_factor(close_prices)
    try:
        RISK_REDIS_CLIENT.set(BTC_RISK_KEY, str(risk_score), ex=43200)
    except Exception as e:
        logging.error(f"Error saving to Redis: {str(e)}", exc_info=True)
    return risk_score

def fetch_btc_history_kraken(pair: str = 'XBTUSD', interval_minutes: int = 1440):
    url = "https://api.kraken.com/0/public/OHLC"
    params = {
        'pair': pair,
        'interval': interval_minutes,
        # since 参数可以省略，直接获取最新的 720 条数据
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data['error']:
            print(f"Kraken API 错误: {data['error']}")
            return None
        
        asset_key = [k for k in data['result'].keys() if k != 'last'][0]
        ohlc_data = data['result'][asset_key]
        df = pd.DataFrame(ohlc_data, columns=[
            'time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'
        ])
        df['close'] = df['close'].astype(float)
        df['date'] = pd.to_datetime(df['time'], unit='s', utc=True)

        if len(df) < 2:
             print("数据点不足以进行风险计算。")
             return None

        return df
    
    except requests.exceptions.RequestException as e:
        print(f"Kraken API 请求失败: {e}")
        return None
    except Exception as e:
        print(f"数据处理失败: {e}")
        return None

def calculate_btc_risk_factor(prices: pd.Series) -> Decimal:
    """
    根据价格序列(close prices)计算BTC风险系数(0-10)
    """
    if len(prices) < 10:
        return Decimal('10')
    
    prices_numeric = prices.astype(float)

    daily_log_returns = np.log(prices_numeric / prices_numeric.shift(1)).dropna()

    vol = daily_log_returns.std() * np.sqrt(365)

    # 最大回撤计算
    prices_array = prices.values
    cumulative_max = np.maximum.accumulate(prices_array)
    drawdown = (prices_array - cumulative_max) / cumulative_max
    max_dd = abs(np.min(drawdown))
    
    if vol < 0.20:
        base = 3
    elif vol < 0.30:
        base = 4
    elif vol < 0.40:
        base = 5
    elif vol < 0.50:
        base = 6
    elif vol < 0.60:
        base = 7
    elif vol < 0.70:
        base = 8
    elif vol < 0.80:
        base = 9
    else:
        base = 10

    dd_adjust = max_dd * 5
    risk = min(10, base + dd_adjust)

    return Decimal(str(round(risk, 2)))