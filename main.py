import redis
from fastapi import FastAPI
from decimal import Decimal
import uvicorn
from models.asset import AssetData

app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, db=0)
GRAMS_TO_OUNCES_TROY = Decimal('0.0321507')

def get_exchange_rate(code):
    try:
        rate = redis_client.get(code)
        return Decimal(rate.decode('utf-8')) if rate else Decimal('0')
    except Exception as e:
        print(f"Error getting exchange rate for {code}: {str(e)}")
        return Decimal('0')

def get_usd_value(money: Decimal, rate: Decimal):
    return (Decimal('1') / rate) * money if rate != Decimal('0') else Decimal('0')

def get_gold_value(grams: Decimal, oz: Decimal, rate: Decimal):
    ounces = grams * GRAMS_TO_OUNCES_TROY + oz
    return ounces * (Decimal('1') / rate) if rate != Decimal('0') else Decimal('0')

@app.get("/")
def calculate():
    return {"message": "Hello, get!"}

@app.post("/update_assets")
async def update_assets(data: AssetData):
    rates = {
        'XAU': get_exchange_rate('XAU'),
        'CNY': get_exchange_rate('CNY'),
        'GBP': get_exchange_rate('GBP'),
        'EUR': get_exchange_rate('EUR'),
        'HKD': get_exchange_rate('HKD'),
        'BTC': get_exchange_rate('BTC'),
        'SGD': get_exchange_rate('SGD')
    }

    values_in_usd = {
        'gold': get_gold_value(data.gold_g, data.gold_oz, rates['XAU']),
        'cny': get_usd_value(data.retirement_funds_cny + data.funds_cny + data.savings_cny + data.housing_fund_cny, rates['CNY']),
        'gbp': get_usd_value(data.deposit_gbp, rates['GBP']),
        'eur': get_usd_value(data.savings_eur + data.funds_eur, rates['EUR']),
        'sgd': get_usd_value(data.savinds_sgd + data.funds_sgd, rates['SGD']),
        'hkd': get_usd_value(data.savings_hkd + data.funds_hkd, rates['HKD']),
        'btc': get_usd_value(data.btc, rates['BTC']) + data.btc_stock_usd,
        'usd': data.savings_usd + data.stock_usd
    }

    savings_in_usd = {
        'cny': get_usd_value(data.savings_cny, rates['CNY']),
        'eur': get_usd_value(data.savings_eur, rates['EUR']),
        'sgd': get_usd_value(data.savinds_sgd, rates['SGD']),
        'hkd': get_usd_value(data.savings_hkd, rates['HKD']),
        'usd': data.savings_usd
    }

    total_assets_usd = sum(values_in_usd.values())
    total_savings_usd = sum(savings_in_usd.values())
    available_liquidity_ratio = total_savings_usd / total_assets_usd * 100
    gold_ratio = values_in_usd['gold'] / total_assets_usd * 100 
    total_btc_usd = values_in_usd['btc']
    btc_ratio = total_btc_usd / total_assets_usd * 100
    return {"message": f"{available_liquidity_ratio}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)