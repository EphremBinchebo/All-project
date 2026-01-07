import numpy as np
import pandas as pd
from dataclasses import dataclass
from ..config import settings


@dataclass
class RegimeResult:
    regime: str              # "trend" or "range"
    volatility_state: str    # "high" or "low"
    slope: float
    vol: float


class RegimeService:
    """
    Simple & robust baselines:
    - Trend vs range from rolling slope of log-price (linear regression)
    - Volatility state from rolling std percentile
    """
    def classify(self, candles: pd.DataFrame) -> RegimeResult:
        close = candles["close"].astype(float).values
        logp = np.log(close + 1e-9)

        window = min(120, len(logp))
        y = logp[-window:]
        x = np.arange(window)

        # Linear regression slope
        x_mean = x.mean()
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / (((x - x_mean) ** 2).sum() + 1e-9)

        # Volatility (rolling std of returns)
        rets = np.diff(logp)
        vol = float(np.std(rets[-window:])) if len(rets) >= window else float(np.std(rets)) if len(rets) else 0.0

        # Volatility state using percentile threshold over recent rolling vol samples
        # For MVP: compare current vol to historical vols from same series
        if len(rets) > 60:
            vols = pd.Series(rets).rolling(30).std().dropna().values
            if len(vols) > 10:
                thr = np.quantile(vols, settings.high_vol_percentile_threshold)
                volatility_state = "high" if vol >= thr else "low"
            else:
                volatility_state = "low"
        else:
            volatility_state = "low"

        regime = "trend" if abs(slope) >= settings.trend_slope_threshold else "range"
        return RegimeResult(regime=regime, volatility_state=volatility_state, slope=float(slope), vol=vol)
