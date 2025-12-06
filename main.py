import redis
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, desc
from decimal import Decimal
import logging
import uvicorn

from models import AssetSnapshot, AssetResults
from database import get_db, create_db_and_tables

app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, db=0)
GRAMS_TO_OUNCES_TROY = Decimal('0.0321507')
CACHE_KEY = 'asset_data'

origins = [
    "https://finassettrackerfrontend.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def save_to_redis(data: AssetSnapshot):
    try: 
        serializable_data = data.model_dump_json()
        redis_client.set(CACHE_KEY, serializable_data)
        return True
    except Exception as e:
        logging.error(f"Error saving to Redis: {str(e)}", exc_info=True)
        return False

def load_from_redis() -> AssetSnapshot:
    try:
        data = redis_client.get(CACHE_KEY)
        if data:
            data_json_string = data.decode('utf-8')
            asset = AssetSnapshot.model_validate_json(data_json_string)
            return asset
        return None
    except Exception as e:
        logging.error(f"Error loading from Redis: {str(e)}", exc_info=True)
        return None

def get_exchange_rate(code: str):
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

def get_value(field) -> Decimal: 
    if field is None or str(field) == "":
        return Decimal('0')
    return Decimal(str(field))

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/", response_model=AssetSnapshot)
def get_latest_asset_data(db: Session = Depends(get_db)):
    cached_data = load_from_redis()

    if cached_data:
        return cached_data
    
    statement = select(AssetSnapshot).order_by(desc(AssetSnapshot.id)).limit(1)
    db_snapshot = db.exec(statement).first()

    if not db_snapshot:
        raise HTTPException(status_code=404, detail="No asset data found in the database.")
    save_to_redis(db_snapshot)
    return db_snapshot

@app.post("/update_assets", response_model=AssetResults)
async def update_assets(
    data: AssetSnapshot,
    db: Session = Depends(get_db)
):
    try:
        # save data to redis
        save_to_redis(data)
        rates = {
            'XAU': get_exchange_rate('XAU'),
            'CNY': get_exchange_rate('CNY'),
            'GBP': get_exchange_rate('GBP'),
            'EUR': get_exchange_rate('EUR'),
            'HKD': get_exchange_rate('HKD'),
            'BTC': get_exchange_rate('BTC'),
            'SGD': get_exchange_rate('SGD')
        }

        cny_total = get_value(data.retirement_funds_cny) + get_value(data.funds_cny) + get_value(data.savings_cny) + get_value(data.housing_fund_cny)
        eur_total = get_value(data.savings_eur) + get_value(data.funds_eur)
        sgd_total = get_value(data.savings_sgd) + get_value(data.funds_sgd)
        hkd_total = get_value(data.savings_hkd) + get_value(data.funds_hkd)

        values_in_usd = {
            'gold': get_gold_value(get_value(data.gold_g), get_value(data.gold_oz), rates['XAU']),
            'cny': get_usd_value(cny_total, rates['CNY']),
            'gbp': get_usd_value(get_value(data.deposit_gbp), rates['GBP']),
            'eur': get_usd_value(eur_total, rates['EUR']),
            'sgd': get_usd_value(sgd_total, rates['SGD']),
            'hkd': get_usd_value(hkd_total, rates['HKD']),
            
            'btc': get_usd_value(get_value(data.btc), rates['BTC']) + get_value(data.btc_stock_usd),
            
            'usd': get_value(data.savings_usd) + get_value(data.stock_usd)
        }

        savings_in_usd = {
            'cny': get_usd_value(get_value(data.savings_cny), rates['CNY']),
            'eur': get_usd_value(get_value(data.savings_eur), rates['EUR']),
            'sgd': get_usd_value(get_value(data.savings_sgd), rates['SGD']),
            'hkd': get_usd_value(get_value(data.savings_hkd), rates['HKD']),
            'usd': get_value(data.savings_usd)
        }

        total_assets_usd = sum(values_in_usd.values())
        total_savings_usd = sum(savings_in_usd.values())

        if total_assets_usd == Decimal('0'):
            available_liquidity_ratio = Decimal('0')
            gold_ratio = Decimal('0')
            btc_ratio = Decimal('0')
        else:
            available_liquidity_ratio = total_savings_usd / total_assets_usd * 100
            gold_ratio = values_in_usd['gold'] / total_assets_usd * 100 
            total_btc_usd = values_in_usd['btc']
            btc_ratio = total_btc_usd / total_assets_usd * 100

        db.add(data)
        db.commit()
        db.refresh(data)
        return AssetResults(
            total_assets_usd=total_assets_usd,
            total_savings_usd=total_savings_usd,
            available_liquidity_ratio=available_liquidity_ratio,
            gold_ratio=gold_ratio,
            btc_ratio=btc_ratio
        )
    
    except Exception as e:
        logging.error(f"Asset calculation or DB error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/clear")
async def clear_data(db: Session = Depends(get_db)):
    try:
        redis_client.delete(CACHE_KEY)
        return {"message": "Data cache cleared successfully."}
    except Exception as e:
        logging.error(f"Redis clear error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear Redis cache.")

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8001)