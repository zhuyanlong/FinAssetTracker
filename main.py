import redis
from fastapi import FastAPI, Depends, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlmodel import Session, select, desc
from decimal import Decimal
import logging
import uvicorn
from datetime import datetime
import os

from models import AssetSnapshot, AssetResults
from database import get_db, create_db_and_tables
from config import (
    RISK_WEIGHTS,
    GRAMS_TO_OUNCES_TROY,
    CACHE_KEY,
    REPORT_DIR,
    REDIS_HOST,
    REDIS_DB,
    REDIS_PORT
)

app = FastAPI()
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

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

        results = AssetResults(
            total_assets_usd=total_assets_usd,
            total_savings_usd=total_savings_usd,
            available_liquidity_ratio=available_liquidity_ratio,
            gold_ratio=gold_ratio,
            btc_ratio=btc_ratio
        )

        report_content = generate_report(data, results)
        filepath = save_report(report_content)

        filename_only = os.path.basename(filepath)
        results.report_path = filename_only

        db.add(data)
        db.commit()
        db.refresh(data)

        return results
    
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

@app.get("/download_report/{filename}")
def download_report(filename: str):
    """
    接收文件名，从'reports'目录读取文件，并将其发送给客户端下载
    """
    filepath = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report file not found.")
    
    return FileResponse(
        path=filepath,
        media_type='text/plain',
        filename=filename
    )

def generate_report(data: AssetSnapshot, results: AssetResults) -> str:
    """生成报告内容"""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    report = f"""Asset Report - Generated at {timestamp}

Original Asset Data:
-------------------
黄金 {data.gold_g} g {data.gold_oz} oz
养老金(CNY) {data.retirement_funds_cny}
基金(CNY) {data.funds_cny}
住房公积金(CNY) {data.housing_fund_cny}
储蓄(CNY) {data.savings_cny}
比特币(个) {data.btc}
比特币股票(USD) {data.btc_stock_usd}
基金(HDK) {data.funds_hkd}
储蓄(HKD) {data.savings_hkd}
基金(SGD) {data.funds_sgd}
储蓄(SGD) {data.savings_sgd}
基金(EUR) {data.funds_eur}
储蓄(EUR) {data.savings_eur}
存款(GBP) {data.deposit_gbp}
股票(USD) {data.stock_usd}
储蓄(USD) {data.savings_usd}

美元计价:
------------------
总资产: {results.total_assets_usd:.2f} USD
总储蓄: {results.total_savings_usd:.2f} USD
黄金资产占比: {results.gold_ratio:.2f}%
比特币资产占比: {results.btc_ratio:.2f}%
"""
    return report

def save_report(report_content: str):
    """保存报告到文件"""
    filename = f"asset_report_{datetime.now().strftime('%Y%m%d')}.txt"
    filepath = os.path.join(REPORT_DIR, filename)

    os.makedirs(REPORT_DIR, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report_content)
    return filepath

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)