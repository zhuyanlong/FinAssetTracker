from sqlmodel import SQLModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel

class AssetDataModelConfig(SQLModel):
    pass

class AssetSnapshot(AssetDataModelConfig, table=True):
    __tablename__ = "asset_data_snapshots_sqlmodel"

    id: Optional[int] = Field(default=None, primary_key=True)
    snapshot_date: datetime = Field(default_factory=datetime.utcnow)

    gold_g: Decimal = Field(default=Decimal('0'), max_digits=18, decimal_places=2)
    gold_oz: Decimal = Field(default=Decimal('0'), max_digits=18, decimal_places=2)
    btc: Decimal = Field(default=Decimal('0'), max_digits=18, decimal_places=8)

    btc_stock_usd: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)
    deposit_gbp: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)

    retirement_funds_cny: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)
    savings_cny: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)
    funds_cny: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)
    housing_fund_cny: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)
    
    funds_sgd: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)
    savings_sgd: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2) 

    funds_eur: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)
    savings_eur: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)

    funds_hkd: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)
    savings_hkd: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)

    savings_usd: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)
    stock_usd: Decimal = Field(default=Decimal('0'), max_digits=15, decimal_places=2)

class AssetResults(SQLModel):
    total_assets_usd: Decimal
    total_savings_usd: Decimal
    available_liquidity_ratio: Decimal
    gold_ratio: Decimal
    btc_ratio: Decimal
    weighted_risk_score: Decimal
    speculative_ratio: Decimal

    report_path: Optional[str] = None
    message: Optional[str] = None

class AgentOutput(BaseModel):
    verdict: str
    summary: str
    suggested_adjustments: Dict[str, float]
    explanations: Dict[str, str]
    confidence: float

class SimulationRequest(BaseModel):
    target_field: str
    delta_amount: Decimal

class SimulationResponse(BaseModel):
    original: AssetResults
    simulated: AssetResults
    diff_summary: Dict[str, str]