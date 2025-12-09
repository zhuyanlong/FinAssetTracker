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

# ===========================
# 金融计算常量
# ===========================
# 克转金衡盎司系数# ===========================
GRAMS_TO_OUNCES_TROY = Decimal('0.0321507')

# ===========================
# 风险评估配置 (Risk Assessment)
# ===========================
# 定义各类资产的风险权重 (0-10)
# 0-1: 无风险, 2-4: 低风险, 5-7: 中高风险, 8-10: 高投机
RISK_WEIGHTS = {
    'savings': Decimal('0.5'),      # 现金/储蓄
    'deposit': Decimal('0.5'),      # 定期存款
    'housing': Decimal('1.0'),      # 公积金
    'retirement': Decimal('1.0'),   # 养老金
    'funds_fixed': Decimal('2.0'),  # 债券/固收基金
    'funds_mixed': Decimal('4.0'),  # 混合型基金
    'gold': Decimal('5.0'),         # 黄金
    'stock': Decimal('8.0'),        # 股票
    'btc': Decimal('10.0')          # 比特币
}
