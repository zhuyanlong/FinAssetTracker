import os
import redis
import logging
import uvicorn

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlmodel import Session, select, desc
from decimal import Decimal
from datetime import datetime
from models import AssetSnapshot, AssetResults, SimulationRequest, SimulationResponse
from vector_store import asset_vector_db
from database import get_db, create_db_and_tables
from risk_engine import update_and_cache_btc_risk
from agent import analyze_snapshot_and_results, snapshot_to_dict
from calculator import calculate_asset_metrics
from config import (
    CACHE_KEY,
    REPORT_DIR,
    REDIS_HOST,
    REDIS_DB,
    REDIS_PORT,
    BTC_RISK_KEY
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

def get_btc_risk_score(redis_client) -> Decimal:
    """从Redis获取风险分, 如果失败, 则计算并存入Redis"""
    cached_risk = redis_client.get(BTC_RISK_KEY)
    if cached_risk:
        try:
            return Decimal(cached_risk.decode('utf-8'))
        except Exception:
            logging.warning("Cached BTC risk factor is corrupted. Recalculating.")
    return update_and_cache_btc_risk()

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
        btc_risk_score = get_btc_risk_score(redis_client)
        results = calculate_asset_metrics(data, rates, btc_risk_score)
        snapshot_dict = snapshot_to_dict(data)
        results_dict = {
            "total_assets_usd": float(results.total_assets_usd),
            "total_savings_usd": float(results.total_savings_usd),
            "available_liquidity_ratio": float(results.available_liquidity_ratio),
            "gold_ratio": float(results.gold_ratio),
            "btc_ratio": float(results.btc_ratio),
            "weighted_risk_score": float(results.weighted_risk_score),
            "speculative_ratio": float(results.speculative_ratio),
            "btc_dynamic_risk": float(btc_risk_score)
        }

        context = {"note": "automated analysis", "date": datetime.utcnow().isoformat()}
        agent_out = analyze_snapshot_and_results(snapshot_dict, results_dict, context=context)

        report_content = generate_report(data, results)

        try:
            vector_metadata = {
                "report_date": data.snapshot_date.strftime("%Y-%m-%d"),
                "total_assets": float(results.total_assets_usd),
                "risk_score": float(results.weighted_risk_score),
                "btc_ratio": float(results.btc_ratio),
                "source": "automated_update"
            }

            asset_vector_db.add_report(report_text=report_content, metadata=vector_metadata)

        except Exception as e:
            logging.error(f"Vector DB storage failed: {e}")
        
        filepath = save_report(report_content)

        filename_only = os.path.basename(filepath)
        results.report_path = filename_only
        results.message = agent_out.summary

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

@app.post("/simulate", response_model=SimulationResponse)
async def simulate_investment(
    request: SimulationRequest,
    db: Session = Depends(get_db)
):
    current_snapshot = load_from_redis()
    if not current_snapshot:
        statement = select(AssetSnapshot).order_by(desc(AssetSnapshot.id)).limit(1)
        current_snapshot = db.exec(statement).first()
        if not current_snapshot:
            raise HTTPException(status_code=404, detail="No baseline data found.")
        
    rates = {
        'XAU': get_exchange_rate('XAU'),
        'CNY': get_exchange_rate('CNY'),
        'GBP': get_exchange_rate('GBP'),
        'EUR': get_exchange_rate('EUR'),
        'HKD': get_exchange_rate('HKD'),
        'BTC': get_exchange_rate('BTC'),
        'SGD': get_exchange_rate('SGD')
    }
    btc_risk = get_btc_risk_score(redis_client)
    original_results = calculate_asset_metrics(current_snapshot, rates, btc_risk)

    simulated_snapshot = original_results.model_copy(deep=True)

    if hasattr(simulated_snapshot, request.target_field):
        original_value = getattr(simulated_snapshot, request.target_field) or Decimal('0')
        new_value = original_value + request.delta_amount
        if new_value < 0: new_value = Decimal('0')

        setattr(simulated_snapshot, request.target_field, new_value)
    else:
        raise HTTPException(status_code=404, detail=f"Invalid field: {request.target_field}")
    
    simulated_results = calculate_asset_metrics(simulated_snapshot, rates, btc_risk)

    diff_summary = {
        "total_assets": f"{original_results.total_assets_usd:.2f} -> {simulated_results.total_assets_usd:.2f}",
        "risk_score": f"{original_results.weighted_risk_score:.2f} -> {simulated_results.weighted_risk_score:.2f}",
        "btc_ratio": f"{original_results.btc_ratio:.2f}% -> {simulated_results.btc_ratio:.2f}%",
        "liquidity": f"{original_results.available_liquidity_ratio:.2f}% -> {simulated_results.available_liquidity_ratio:.2f}%"
    }

    return SimulationResponse(
        original=original_results,
        simulated=simulated_results,
        diff_summary=diff_summary
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