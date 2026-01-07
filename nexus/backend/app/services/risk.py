from dataclasses import dataclass
from ..config import settings


@dataclass
class RiskResult:
    final_risk_pct: float
    position_size_usd: float
    reasons: list[str]


class RiskService:
    """
    Simple risk sizing:
    - start with intended risk pct
    - cap at max risk per trade
    - reduce risk in high volatility
    - position size = equity * risk_pct / stop_distance_pct
      (This assumes stop distance is expressed as % move against entry)
    """
    def compute(self, account_equity: float, intended_risk_pct: float, stop_distance_pct: float, volatility_state: str) -> RiskResult:
        reasons: list[str] = []

        risk_pct = min(intended_risk_pct, settings.max_risk_per_trade_pct)
        if intended_risk_pct > settings.max_risk_per_trade_pct:
            reasons.append(f"Risk capped to {settings.max_risk_per_trade_pct:.2f}% (beginner-safe limit).")

        if volatility_state == "high":
            risk_pct = min(risk_pct, 0.5)  # reduce in high vol for beginners
            reasons.append("High volatility detected → risk reduced to 0.50%.")

        # Avoid divide-by-zero
        stop_distance_pct = max(stop_distance_pct, 0.05)  # minimum stop distance 0.05%
        # Position sizing: how much notional you can take so that stop hit loses risk% of equity
        position_size_usd = account_equity * (risk_pct / 100.0) / (stop_distance_pct / 100.0)

        return RiskResult(final_risk_pct=risk_pct, position_size_usd=float(position_size_usd), reasons=reasons)
