from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np

from .regime import RegimeService, RegimeResult


@dataclass
class MultiTFRegime:
    final_regime: str          # "trend" or "range"
    final_volatility: str      # "high" or "low"
    confidence: float          # 0..1
    per_tf: Dict[str, RegimeResult]


class MultiTimeframeRegimeService:
    """
    Combines multiple timeframe regime classifications into one.
    Heuristic (good MVP):
    - Majority vote for regime
    - Volatility is "high" if >=2 timeframes high
    - Confidence increases when timeframes agree
    """
    def __init__(self):
        self.base = RegimeService()

    def combine(self, per_tf: Dict[str, RegimeResult]) -> MultiTFRegime:
        regimes = [r.regime for r in per_tf.values()]
        vols = [r.volatility_state for r in per_tf.values()]

        trend_votes = sum(1 for x in regimes if x == "trend")
        range_votes = len(regimes) - trend_votes
        final_regime = "trend" if trend_votes > range_votes else "range"

        high_vol_votes = sum(1 for x in vols if x == "high")
        final_vol = "high" if high_vol_votes >= 2 else "low"

        # Confidence: agreement-based + slope strength bonus
        agree_regime = max(trend_votes, range_votes) / max(1, len(regimes))
        agree_vol = (high_vol_votes if final_vol == "high" else (len(vols) - high_vol_votes)) / max(1, len(vols))

        # Slope strength (normalize)
        slopes = np.array([abs(r.slope) for r in per_tf.values()], dtype=float)
        slope_bonus = float(np.clip(slopes.mean() / 0.002, 0.0, 1.0))  # tuned rough scale

        confidence = float(np.clip(0.55 * agree_regime + 0.25 * agree_vol + 0.20 * slope_bonus, 0.0, 1.0))

        return MultiTFRegime(
            final_regime=final_regime,
            final_volatility=final_vol,
            confidence=confidence,
            per_tf=per_tf
        )
