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
from models import (
    AssetSnapshot, 
    AssetResults, 
    AdvancedSimulationRequest, 
    SimulationResponse,
    ActionType
)
from vector_store import asset_vector_db
from database import get_db, create_db_and_tables
from risk_engine import update_and_cache_btc_risk
from agent import analyze_snapshot_and_results, snapshot_to_dict
from calculator import calculate_asset_metrics
from allocation_engine import calculate_strategic_rebalancing
from config import (
    CACHE_KEY,
    REPORT_DIR,
    REDIS_HOST,
    REDIS_DB,
    REDIS_PORT,
    BTC_RISK_KEY,
    TARGET_ALLOCATION,
    REBALANCE_THRESHOLD,
    FX_REFERENCE
)
from onchain_analyzer import generate_btc_onchain_report
from utils import (
    get_asset_info,
    get_usd_value
)

app = FastAPI()
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

origins = [
    "https://asset.yanlongzhu.space",
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
        logging.error(f"Error getting exchange rate for {code}: {str(e)}")
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
            'SGD': get_exchange_rate('SGD'),
            'USD': get_exchange_rate('USD')
        }
        btc_risk_score = get_btc_risk_score(redis_client)
        results = calculate_asset_metrics(data, rates, btc_risk_score)

        market_report_text = generate_btc_onchain_report()
        logging.info(f"Market Report Generatedd: {market_report_text.strip()}")

        try:
            vector_metadata = {
                "report_date": data.snapshot_date.strftime("%Y-%m-%d"),
                "source": "market_sentiment",
                "type": "btc_fng"
            }
            asset_vector_db.add_report(report_text=market_report_text, metadata=vector_metadata)
        except Exception as e:
            logging.error(f"Vector DB storage failed: {e}")

        strategic_suggestions = calculate_strategic_rebalancing(
            results=results,
            target_map=TARGET_ALLOCATION,
            threshold=REBALANCE_THRESHOLD,
            current_rates=rates,
            fx_refs=FX_REFERENCE
        )

        strategy_msg = []

        if not strategic_suggestions:
            strategy_msg.append("资产配置与汇率估值均在健康区间")
        else:
            for item in strategic_suggestions:
                icon = "🚨" if "STRONG" in item.action else "💡"
                strategy_msg.append(
                    f"{icon} {item.asset_class}: {item.action} | 偏差:{item.drift:+.1f}% | 汇率:{item.fx_status} | {item.reason}"
                )

        formatted_strategy_text = "\n".join(strategy_msg)

        snapshot_dict = snapshot_to_dict(data)
        results_dict = {
            "total_assets_usd": float(results.total_assets_usd),
            "total_savings_usd": float(results.total_savings_usd),
            "available_liquidity_ratio": float(results.available_liquidity_ratio),
            "gold_ratio": float(results.gold_ratio),
            "btc_ratio": float(results.btc_ratio),
            "weighted_risk_score": float(results.weighted_risk_score),
            "speculative_ratio": float(results.speculative_ratio),
            "btc_dynamic_risk": float(btc_risk_score),
            "currency_distribution": results.currency_distribution,
            "strategic_advice": formatted_strategy_text,
        }

        context = {
            "note": "automated analysis", 
            "date": datetime.utcnow().isoformat(),
            "market_sentiment_analysis": market_report_text,
            "user_intent": "User is actively DCAing into BTC.",
            "fx_market_status": "Analyst provided strategic rebalancing advice based on FX valuation."
        }
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
        results.message = f"{agent_out.summary}\n\n【量化策略建议】:\n{formatted_strategy_text}"

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
    request: AdvancedSimulationRequest,
    db: Session = Depends(get_db)
):
    # 1. 获取基准数据
    current_snapshot = load_from_redis()
    if not current_snapshot:
        statement = select(AssetSnapshot).order_by(desc(AssetSnapshot.id)).limit(1)
        current_snapshot = db.exec(statement).first()
        if not current_snapshot:
            raise HTTPException(status_code=404, detail="No baseline data found.")
        
    # 2. 获取实时环境数据
    rates = {
        'XAU': get_exchange_rate('XAU'),
        'CNY': get_exchange_rate('CNY'),
        'GBP': get_exchange_rate('GBP'),
        'EUR': get_exchange_rate('EUR'),
        'HKD': get_exchange_rate('HKD'),
        'BTC': get_exchange_rate('BTC'),
        'SGD': get_exchange_rate('SGD'),
        'USD': get_exchange_rate('USD')
    }
    btc_risk = get_btc_risk_score(redis_client)
    original_results = calculate_asset_metrics(current_snapshot, rates, btc_risk)

    # 3. 拷贝
    simulated_snapshot = current_snapshot.model_copy(deep=True)

    simulation_logs = [] # 用于记录转换过程

    for action in request.actions:
        if action.type == ActionType.ADJUST:
            if hasattr(simulated_snapshot, action.from_field):
                old_val = getattr(simulated_snapshot, action.from_field) or Decimal('0')
                new_val = Decimal(old_val) + action.amount
                if new_val < 0: new_val = Decimal('0')
                setattr(simulated_snapshot, action.from_field, new_val)

                name = get_asset_info(action.from_field)['name']
                # :+ 是什么含义呢
                simulation_logs.append(f"Adjusted {name} by {action.amount:+}")
            else:
                logging.warning(f"Field: {action.from_field} not found")
        elif action.type == ActionType.TRANSFER:
            if not action.to_field:
                continue

            field_src = action.from_field
            field_dst = action.to_field

            info_src = get_asset_info(field_src)
            info_dst = get_asset_info(field_dst)

            src_balance = getattr(simulated_snapshot, field_src) or Decimal('0')
            transfer_amount = Decimal(abs(action.amount))
            src_balance = Decimal(src_balance)
            logging.info(f"field_src: {field_src}, field_dst: {field_dst}, info_src: {info_src}, info_dst: {info_dst}, src_balance:{src_balance}, transfer_amount {transfer_amount}")

            setattr(simulated_snapshot, field_src, src_balance - transfer_amount)

            rate_src = rates.get(info_src['currency'], Decimal('0'))
            rate_dst = rates.get(info_dst['currency'], Decimal('0'))

            scale_src = Decimal(str(info_src['unit_scale']))
            scale_dst = Decimal(str(info_dst['unit_scale']))

            if rate_dst > 0:
                value_in_usd = get_usd_value(transfer_amount, scale_src, rate_src)

                amount_dst = value_in_usd * rate_dst / scale_dst
                dst_balance = getattr(simulated_snapshot, field_dst) or Decimal('0')
                setattr(simulated_snapshot, field_dst, Decimal(dst_balance) + Decimal(amount_dst))

                log_msg = (
                    f"划转: {info_src['name']} ({transfer_amount}) -> {info_dst['name']} ({amount_dst:.4f})"
                )
                simulation_logs.append(log_msg)
            
    # 4. 重新计算模拟后的指标
    simulated_results = calculate_asset_metrics(simulated_snapshot, rates, btc_risk)

    logging.info(f"original: {current_snapshot.savings_cny}, sim: {simulated_snapshot.savings_cny}")

    # 5. 调用Agent获取模拟决策的意见
    sim_snapshot_dict = snapshot_to_dict(simulated_snapshot)
    sim_results_dict = {
        "total_assets_usd": float(simulated_results.total_assets_usd),
        "weighted_risk_score": float(simulated_results.weighted_risk_score),
        "btc_ratio": float(simulated_results.btc_ratio),
        "available_liquidity_ratio": float(simulated_results.available_liquidity_ratio)
    }

    sim_context = {
        "note": f"SIMULATION ONLY: {request.notes}",
        "actions_log": "; ".join(simulation_logs)
    }

    agent_feedback = analyze_snapshot_and_results(sim_snapshot_dict, sim_results_dict, context=sim_context)

    diff_summary = {
        "total_assets": f"{original_results.total_assets_usd:.2f} -> {simulated_results.total_assets_usd:.2f}",
        "risk_score": f"{original_results.weighted_risk_score:.2f} -> {simulated_results.weighted_risk_score:.2f}",
        # "btc_ratio": f"{original_results.btc_ratio:.2f}% -> {simulated_results.btc_ratio:.2f}%",
        "liquidity": f"{original_results.available_liquidity_ratio:.2f}% -> {simulated_results.available_liquidity_ratio:.2f}%",
        "agent_verdict": agent_feedback.verdict,
        "agent_advice": agent_feedback.summary,
        # "logs": simulation_logs,
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