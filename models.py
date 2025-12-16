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

    currency_distribution: Dict[str, Decimal] = {}

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

class FXConversionSuggestion:
    def __init__(
        self,
        from_currency: str,
        to_currency: str,
        amount_usd: Decimal,
        reason: str
    ):
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.amount_usd = amount_usd
        self.reason = reason

class SmartSuggestion:
    def __init__(
        self,
        asset_class: str,
        current_pct: Decimal,
        target_pct: Decimal,
        drift: Decimal,
        fx_status: str,
        action: str,
        amount_usd: Decimal,
        reason: str
    ):
        self.asset_class = asset_class
        self.current_pct = current_pct
        self.target_pct = target_pct
        self.drift = drift
        self.fx_status = fx_status
        self.action = action
        self.amount_usd = amount_usd
        self.reason = reason