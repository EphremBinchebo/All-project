from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal, List, Optional


class CheckTradeRequest(BaseModel):
    user_id: str = Field(..., description="UUID string for the user")
    symbol: str = Field(..., examples=["BTCUSDT"])
    strategy: str = Field(..., examples=["mean_reversion", "breakout"])
    account_equity: float = Field(..., gt=0, description="Paper account equity in USD (or quote currency)")
    intended_risk_pct: float = Field(..., gt=0, description="Requested risk % per trade (e.g., 1.0)")
    stop_distance_pct: float = Field(..., gt=0, description="Stop distance as % of entry price (e.g., 0.5)")
    timeframe: str = Field("1m", examples=["1m", "5m", "15m"])


Decision = Literal["ALLOW", "WARN", "BLOCK"]


class CheckTradeResponse(BaseModel):
    decision: Decision
    quality_score: float
    risk_pct: float
    position_size_usd: float
    reasons: List[str]
    suggested_actions: List[str]
    market_regime: str
    volatility_state: str


class TradeOpenRequest(BaseModel):
    user_id: str
    symbol: str
    strategy: str
    entry_price: float
    qty: float
    risk_pct: float
    stop_distance_pct: float
    mode: Literal["PAPER", "LIVE"] = "PAPER"
    notes: Optional[str] = None


class TradeCloseRequest(BaseModel):
    user_id: str
    trade_id: str
    exit_price: float
    pnl: float
    rr: Optional[float] = None
    rule_violation: bool = False
    notes: Optional[str] = None


class TradeOut(BaseModel):
    id: str
    user_id: str
    symbol: str
    strategy: str
    mode: str
    status: str
    opened_at: datetime
    closed_at: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    qty: float
    risk_pct: float
    stop_distance_pct: float
    pnl: Optional[float]
    rr: Optional[float]
    rule_violation: bool
    notes: Optional[str]

    class Config:
        from_attributes = True


class DailyReport(BaseModel):
    day: str
    trades: int
    wins: int
    losses: int
    realized_pnl: float
    consecutive_losses: int
    cooldown_until: Optional[str]


class WeeklyReport(BaseModel):
    start_day: str
    end_day: str
    trades: int
    wins: int
    losses: int
    realized_pnl: float
    max_consecutive_losses: int

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
