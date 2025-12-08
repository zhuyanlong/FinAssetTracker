import requests
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from config import (
    COINBASE_API_KEY,
    COINBASE_API_SECRET,
    GRANULARITY,
    LIMIT,
    REQUEST_PATH,
    BASE_URL,
    METHOD
)

def get_coinbase_headers(method, request_path, body=""):
    pass

def fetch_btc_history(days: int = 90, granularity: int = 86400):
    """
    从Coinbase Exchane API获取BTC-USD最近days填的历史OHLC数据
    granularity: 采样频率（秒），默认 86400 = dail
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    start_iso = start.isoformat().replace('+00:00', 'Z')
    end_iso = end.isoformat().replace('+00:00', 'Z')
    url = (
        "https://api.pro.coinbase.com/products/BTC-USD/candles"
        f"?start={start_iso}&end={end_iso}&granularity={granularity}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data or not isinstance(data, list) or len(data) == 0:
            print("错误: API 返回数据为空或格式不正确。")
            return None
        
        df = pd.DataFrame(data, columns=['time', 'low', 'high', 'open', 'close', 'volume'])

        df['date'] = pd.to_datetime(df['time'], unit='s')
        df = df.sort_values('date')
        df = df.reset_index(drop=True)
        return df
    except requests.exceptions.RequestException as e:
        print(f"API请求失败: {e}")
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

def main():
    df = fetch_btc_history(days=300)
    if df is not None:
        close_prices = df['close']
        btc_risk = calculate_btc_risk_factor(close_prices)
        volatility = calculate_btc_risk_factor(close_prices.iloc[:1]).__getattribute__('_val')
        max_dd = calculate_btc_risk_factor(close_prices.iloc[:1]).__getattribute__('_val')
        print("-" * 30)
        print(f"基于 {len(close_prices)} 天数据的风险分析")
        print("动态BTC风险系数 (0-10):", btc_risk)
        print("-" * 30)
    else:
        print("无法计算风险系数：未能获取历史数据。")

if __name__ == "__main__":
    main()