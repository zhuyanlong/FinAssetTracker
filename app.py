import redis
from flask import Flask, render_template, request, jsonify, send_file
from decimal import Decimal
import json
from datetime import datetime
import os

redis_client = redis.Redis(host='localhost', port=6379, db=0)
app = Flask(__name__)
CACHE_KEY = 'asset_data'  # Redis 缓存键名

def save_to_redis(data):
    """将数据保存到Redis"""
    try:
        # 将Decimal对象转换为字符串以便JSON序列化
        serializable_data = {k: str(v) for k, v in data.items()}
        redis_client.set(CACHE_KEY, json.dumps(serializable_data))
        return True
    except Exception as e:
        print(f"Error saving to Redis: {str(e)}")
        return False

def load_from_redis():
    """从Redis加载数据"""
    try:
        data = redis_client.get(CACHE_KEY)
        if data:
            # 将JSON字符串转换回字典，并将数值转换为Decimal
            data_dict = json.loads(data)
            return {k: Decimal(v) for k, v in data_dict.items()}
        return get_default_data()
    except Exception as e:
        print(f"Error loading from Redis: {str(e)}")
        return get_default_data()

def get_default_data():
    """获取默认数据"""
    return {
        'gold_g': Decimal('0'),
        'retirement_funds_cny': Decimal('0'),
        'funds_cny': Decimal('0'),
        'housing_fund_cny': Decimal('0'),
        'stock_usd': Decimal('0'),
        'btc': Decimal('0'),
        'usdt': Decimal('0'),
        'usdc': Decimal('0'),
        'savings_cny': Decimal('0'),
        'savings_usd': Decimal('0'),
        'savings_gbp': Decimal('0'),
        'savings_eur': Decimal('0'),
        'savings_sgd': Decimal('0')
    }

def get_exchange_rate(code):
    try:
        rate = redis_client.get(code)
        return Decimal(rate.decode('utf-8')) if rate else Decimal('0')
    except Exception as e:
        print(f"Error getting exchange rate for {code}: {str(e)}")
        return Decimal('0')

def get_usd_value(money, rate):
    return (Decimal('1') / rate) * money if rate != Decimal('0') else Decimal('0')

def get_gold_value(grams, oz, rate):
    GRAMS_TO_OUNCES = Decimal('0.03527396')
    ounces = grams * GRAMS_TO_OUNCES + oz
    return ounces * (Decimal('1') / rate) if rate != Decimal('0') else Decimal('0')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # 获取表单数据并转换为Decimal
            form_data = {
                'gold_g': Decimal(request.form.get('gold_g', '0')),
                'gold_oz': Decimal(request.form.get('gold_oz', '0')),
                'retirement_funds_cny': Decimal(request.form.get('retirement_funds_cny', '0')),
                'funds_cny': Decimal(request.form.get('funds_cny', '0')),
                'housing_fund_cny': Decimal(request.form.get('housing_fund_cny', '0')),
                'stock_usd': Decimal(request.form.get('stock_usd', '0')),
                'btc': Decimal(request.form.get('btc', '0')),
                'usdt': Decimal(request.form.get('usdt', '0')),
                'usdc': Decimal(request.form.get('usdc', '0')),
                'savings_cny': Decimal(request.form.get('savings_cny', '0')),
                'savings_usd': Decimal(request.form.get('savings_usd', '0')),
                'savings_gbp': Decimal(request.form.get('savings_gbp', '0')),
                'savings_eur': Decimal(request.form.get('savings_eur', '0')),
                'savings_sgd': Decimal(request.form.get('savings_sgd', '0'))
            }
            
            # 保存数据到Redis
            save_to_redis(form_data)

            # 计算各类资产的美元价值
            rates = {
                'XAU': get_exchange_rate('XAU'),
                'CNY': get_exchange_rate('CNY'),
                'GBP': get_exchange_rate('GBP'),
                'EUR': get_exchange_rate('EUR'),
                'BTC': get_exchange_rate('BTC'),
                'SGD': get_exchange_rate('SGD'),
                'USDT': get_exchange_rate('USDT'),
                'USDC': get_exchange_rate('USDC')
            }

            # 计算各类资产的美元价值
            values_in_usd = {
                'gold': get_gold_value(form_data['gold_g'], form_data['gold_oz'], rates['XAU']),
                'cny': get_usd_value(
                    form_data['retirement_funds_cny'] + 
                    form_data['funds_cny'] + 
                    form_data['savings_cny'] + 
                    form_data['housing_fund_cny'],
                    rates['CNY']
                ),
                'gbp': get_usd_value(form_data['savings_gbp'], rates['GBP']),
                'eur': get_usd_value(form_data['savings_eur'], rates['EUR']),
                'sgd': get_usd_value(form_data['savings_sgd'], rates['SGD']),
                'btc': get_usd_value(form_data['btc'], rates['BTC']),
                'usdt': get_usd_value(form_data['usdt'], rates['USDT']),
                'usdc': get_usd_value(form_data['usdc'], rates['USDC'])
            }

            # 计算总资产
            total_assets_usd = sum(values_in_usd.values()) + form_data['savings_usd'] + form_data['stock_usd']

            report_content = generate_report(form_data, values_in_usd, total_assets_usd)
            report_path = save_report(report_content)

            # 返回模板，添加报告文件路径
            return render_template(
                'index.html',
                **form_data,
                total_assets_usd=float(total_assets_usd),
                asset_distribution=values_in_usd,
                report_path=report_path
            )

        except Exception as e:
            print(f"Error processing form: {str(e)}")
            return render_template('index.html', error="An error occurred while processing your request.")
    saved_data = load_from_redis()
    return render_template('index.html', **saved_data)

def generate_report(form_data, values_in_usd, total_assets_usd):
    """生成报告内容"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = f"""Asset Report - Generated at {timestamp}

Original Asset Data:
------------------
Gold: {form_data['gold_g']} g
Retirement Funds (CNY): {form_data['retirement_funds_cny']}
Funds (CNY): {form_data['funds_cny']}
Housing Fund (CNY): {form_data['housing_fund_cny']}
Stock (USD): {form_data['stock_usd']}
BTC: {form_data['btc']}
USDT: {form_data['usdt']}
USDC: {form_data['usdc']}
Savings (CNY): {form_data['savings_cny']}
Savings (USD): {form_data['savings_usd']}
Savings (GBP): {form_data['savings_gbp']}
Savings (EUR): {form_data['savings_eur']}
Savings (SGD): {form_data['savings_sgd']}

Assets in USD:
------------
Gold: ${values_in_usd['gold']:.2f}
CNY Assets: ${values_in_usd['cny']:.2f}
GBP Assets: ${values_in_usd['gbp']:.2f}
EUR Assets: ${values_in_usd['eur']:.2f}
SGD Assets: ${values_in_usd['sgd']:.2f}
BTC Assets: ${values_in_usd['btc']:.2f}
USDT Assets: ${values_in_usd['usdt']:.2f}
USDC Assets: ${values_in_usd['usdc']:.2f}
Direct USD Assets: ${float(form_data['savings_usd'] + form_data['stock_usd']):.2f}

Total Assets: ${float(total_assets_usd):.2f} USD
"""
    return report

def save_report(report_content):
    """保存报告到文件"""
    filename = f"asset_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = os.path.join('reports', filename)
    
    # 确保reports目录存在
    os.makedirs('reports', exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report_content)
    return filepath

@app.route('/download_report/<path:filename>')
def download_report(filename):
    """下载报告文件"""
    try:
        return send_file(
            f'reports/{filename}',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 404

# 添加清除数据的路由
@app.route('/clear')
def clear():
    try:
        redis_client.delete(CACHE_KEY)
        return jsonify({"message": "Data cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
