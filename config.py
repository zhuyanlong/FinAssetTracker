import os
from decimal import Decimal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ===========================
# 报告下载目录
# ===========================
REPORT_DIR = os.path.join(BASE_DIR, 'reports')
os.makedirs(REPORT_DIR, exist_ok=True)

# ===========================
# Redis 配置
# ===========================
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
CACHE_KEY = 'asset_data'

# Redis Key for BTC Risk Factor
BTC_RISK_KEY = 'btc_volatility_risk_score'

BTC_PAIR = 'XBTUSD'
BTC_INTERVAL_MINUTES = 1440

BTC_RISK_WEIGHTS = {
    'volatility': Decimal('0.6'),
    'mdd': Decimal('0.4')
}

VOLATILITY_WINDOW = 30
MOD_WINDOW = 365

OPENAI_API_KEY = os.getenv("OPENAI_KEY")
AGENT_CACHE_TTL = int(os.getenv("AGENT_CACHE_TTL", "3600"))

# 各种货币的比例
TARGET_ALLOCATION = {
    "CNY": Decimal('30.0'),
    "USD": Decimal('10.0'),
    "XAU": Decimal('30.0'),
    "BTC": Decimal('20.0'),

    "SGD": Decimal('4.0'),
    "EUR": Decimal('5.0'),
    "GBP": Decimal('1.0'),
    "OTHER": Decimal('0.0')
}

REBALANCE_THRESHOLD = Decimal('5.0')

FX_REFERENCE = {
    "CNY": Decimal("6.95"), # 人民币相对美元的参考汇率
    "EUR": Decimal("0.85"), # 欧元相对美元的参考汇率
    "GBP": Decimal("0.75"), # 英镑相对美元的参考汇率
    "SGD": Decimal("1.29") # 新元相对美元的参考汇率
}

ASSET_APY = {
    # 人民币资产
    'savings_cny': 0.015,
    'funds_cny': 0.03,
    'housing_fund_cny': 0.015,
    'retirement_funds_cny': 0.03,

    # 美元资产
    'savings_usd': 0.04,
    'stock_usd': 0.015, # 美股股息率
    'btc_stock_usd': 0.0,

    # 港币资产
    'savings_hkd': 0.03,
    'funds_hdk': 0.04,

    # 新元资产
    'savings_eur': 0.03,
    'funds_sgd': 0.04,

    # 欧元/英镑
    'savings_eur': 0.03,
    'funds_eur': 0.04,
    'savings_eur': 0.02,
    'deposit_gbp': 0.04
}

ASSET_CONFIG = {
    # --- 人民币资产(CNY) ---
    "savings_cny": {
        "currency": "CNY", "risk": 0.5, "liquid": True, "unit_scale": 1.0, "name": "人民币储蓄"
    },
    "funds_cny": {
        "currency": "CNY", "risk": 4.0, "liquid": False, "unit_scale": 1.0, "name": "人民币基金"
    },
    "retirement_funds_cny": {
        "currency": "CNY", "risk": 1.0, "liquid": False, "unit_scale": 1.0, "name": "养老金"
    },
    "housing_fund_cny": {
        "currency": "CNY", "risk": 1.0, "liquid": False, "unit_scale": 1.0, "name": "公积金"
    },

    # --- 美元资产(USD) ---
    "savings_usd": {
        "currency": "USD", "risk": 0.5, "liquid": True, "unit_scale": 1.0, "name": "美元储蓄"
    },
    "stock_usd": {
        "currency": "USD", "risk": 6.0, "liquid": False, "unit_scale": 1.0, "name": "美股账户"
    },
    "btc_stock_usd": {
        "currency": "USD", "risk": 10.0, "liquid": False, "unit_scale": 1.0, "name": "比特币股票"
    },

    # --- 贵金属/加密货币 ---
    "gold_g": {
        "currency": "XAU", "risk": 2.0, "liquid": False, "unit_scale": 1/31.1035, "name": "黄金(g)"
    },
    "gold_oz": {
        "currency": "XAU", "risk": 2.0, "liquid": False, "unit_scale": 1.0, "name": "黄金(oz)"
    },
    "btc": {
        "currency": "BTC", "risk": 10.0, "liquid": False, "unit_scale": 1.0, "name": "比特币"
    },

    # --- 其他外币 ---
    "savings_hkd": {
        "currency": "HKD", "risk": 0.5, "liquid": True, "unit_scale": 1.0, "name": "港币储蓄"
    },
    "funds_hkd": {
        "currency": "HKD", "risk": 4.0, "liquid": False, "unit_scale": 1.0, "name": "港币基金"
    },
    "savings_sgd": {
        "currency": "SGD", "risk": 0.5, "liquid": True, "unit_scale": 1.0, "name": "新元储蓄"
    },
    "funds_sgd": {
        "currency": "SGD", "risk": 3.0, "liquid": False, "unit_scale": 1.0, "name": "新元基金"
    },
    "savings_eur": {
        "currency": "EUR", "risk": 0.5, "liquid": True, "unit_scale": 1.0, "name": "欧元储蓄"
    },
    "funds_eur": {
        "currency": "EUR", "risk": 3.0, "liquid": False, "unit_scale": 1.0, "name": "欧元基金"
    },
    "deposit_gbp": {
        "currency": "GBP", "risk": 0.5, "liquid": False, "unit_scale": 1.0, "name": "英镑存款"
    }
}