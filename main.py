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
    return {"message": "Hello, post!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)