import requests
import pandas as pd
import numpy as np
import redis
import logging

from decimal import Decimal, ROUND_HALF_UP
from config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    BTC_RISK_KEY,
    BTC_PAIR,
    BTC_INTERVAL_MINUTES, BTC_RISK_WEIGHTS,
    VOLATILITY_WINDOW,
    MOD_WINDOW
)

RISK_REDIS_CLIENT = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

def update_and_cache_btc_risk() -> Decimal:
    """
    获取 BTC 历史数据，计算风险系数，并将结果存储到 Redis。
    """
    df = fetch_btc_history_kraken(pair=BTC_PAIR, interval_minutes=BTC_INTERVAL_MINUTES)
    if df is None or len(df) < MOD_WINDOW:
        logging.warning("数据不足, 使用默认配置的静态权重")
        risk_score = 10.0
    else:
        df_1y = df.tail(365).copy()

        close_prices = df_1y['close']
        risk_score = calculate_btc_risk_factor(close_prices)
    
    try:
        RISK_REDIS_CLIENT.set(BTC_RISK_KEY, str(risk_score), ex=43200)
    except Exception as e:
        logging.error(f"Error saving to Redis: {str(e)}", exc_info=True)
    return risk_score

def fetch_btc_history_kraken(pair: str, interval_minutes: int) -> pd.DataFrame | None:
    url = "https://api.kraken.com/0/public/OHLC"
    params = {
        'pair': pair,
        'interval': interval_minutes,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data['error']:
            logging.error(f"Kraken API 错误: {data['error']}")
            return None
        
        asset_key = [k for k in data['result'].keys() if k != 'last'][0]
        ohlc_data = data['result'][asset_key]
        df = pd.DataFrame(ohlc_data, columns=[
            'time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'
        ])
        df['close'] = df['close'].astype(float)
        df['date'] = pd.to_datetime(df['time'], unit='s', utc=True)

        df = df.sort_values('date').reset_index(drop=True)

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
    prices_numeric = prices.astype(float)
    # 1. 计算收益率并去极端值
    # 计算对数收益率
    log_returns = np.log(prices_numeric / prices_numeric.shift(1)).dropna()
    # 去除1%和99%分位数的极端值
    lower_bound = log_returns.quantile(0.01)
    upper_bound = log_returns.quantile(0.99)
    clipped_returns = log_returns.clip(lower=lower_bound, upper=upper_bound)

    # 2. 动态波动率评分
    # 计算滚动波动率
    rolling_vol = clipped_returns.rolling(window=VOLATILITY_WINDOW).std()

    current_vol = rolling_vol.iloc[-5:].mean()

    # 基于历史分位数打分
    valid_historyvols = rolling_vol.dropna()
    if len(valid_historyvols) > 0:
        vol_percentile = (valid_historyvols < current_vol).mean()
        vol_score = vol_percentile * 10.0
    else:
        vol_score = 5.0

    # 3. 滚动最大回撤评分
    rolling_max = prices_numeric.rolling(window=MOD_WINDOW, min_periods=1).max()
    daily_drawdown = (prices_numeric / rolling_max) - 1.0
    current_mdd = abs(daily_drawdown.iloc[-5:].min())

    mdd_score = (current_mdd / 0.70) * 10.0
    mdd_score = min(10.0, mdd_score)

    # 4. 加权计算最终风险
    final_score = (
        Decimal(str(vol_score)) * BTC_RISK_WEIGHTS['volatility'] +
        Decimal(str(mdd_score)) * BTC_RISK_WEIGHTS['mdd']
    )

    final_score = max(Decimal('0'), min(Decimal('10'), final_score))

    logging.info(f"BTC Risk Calc | Vol: {current_vol:.2%} (Score: {vol_score:.2f}) | "
                 f"MDD: {current_mdd:.2%} (Score: {mdd_score:.2f}) | "
                 f"Final: {final_score:.2f}")

    return final_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)