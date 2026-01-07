from dataclasses import dataclass
from typing import List

# ✅ Required services
from .regime_multi import MultiTimeframeRegimeService
from .risk import RiskService
from .behavior import BehaviorService
from .session import SessionService
from pydantic import BaseModel
from typing import List, Optional


# =========================
# Result DTO
# =========================
@dataclass
class DecisionResult(BaseModel):
    decision: str
    quality_score: float
    risk_pct: float
    position_size_usd: float

    reasons: List[str]
    suggested_actions: List[str]

    market_regime: str
    volatility_state: str

    # ✅ session-aware but OPTIONAL
    session_name: Optional[str] = None
    session_confidence: Optional[float] = None
# @dataclass
# class DecisionResult:
#     decision: str                  # ALLOW | WARN | BLOCK
#     quality_score: float
#     risk_pct: float
#     position_size_usd: float
#     reasons: List[str]
#     suggested_actions: List[str]
#     market_regime: str
#     volatility_state: str
#     session=session["name"],
#     session_note=session["note"],


# =========================
# Decision Service
# =========================
class DecisionService:
    def __init__(self):
        self.multi_regime = MultiTimeframeRegimeService()
        self.risk = RiskService()
        self.behavior = BehaviorService()

    # -------------------------------------------------
    # Simple evaluation (used by dashboard preview)
    # -------------------------------------------------
    def evaluate(self, quality_score: float):
        if quality_score < 0.5:
            return {
                "status": "WARN",
                "recommended_risk": 0.5,
                "regime": "RANGE",
                "advice": [
                    "Wait for 15m confirmation",
                    "Reduce size or skip trade",
                    "Consider mean-reversion",
                ],
            }

        return {
            "status": "OK",
            "recommended_risk": 1.0,
            "regime": "TREND",
            "advice": ["Trade allowed"],
        }

    # -------------------------------------------------
    # Full trade validation engine (CORE NEXUS LOGIC)
    # -------------------------------------------------
    def check_trade(
        self,
        db,
        candles_by_tf: dict,
        user_id: str,
        symbol: str,
        strategy: str,
        account_equity: float,
        intended_risk_pct: float,
        stop_distance_pct: float,
        timeframe: str,
        session = SessionService().detect()
    ) -> DecisionResult:
        
        # 1️⃣ Behavior / discipline checks
        beh = self.behavior.check(db, user_id)

        # 2️⃣ Multi-timeframe regime detection
        per_tf = {
            tf: self.multi_regime.base.classify(df)
            for tf, df in candles_by_tf.items()
        }
        multi = self.multi_regime.combine(per_tf)

        # 3️⃣ Risk computation
        risk = self.risk.compute(
            account_equity,
            intended_risk_pct,
            stop_distance_pct,
            multi.final_volatility,
        )

        # apply session risk multiplier
        risk.final_risk_pct *= session["risk_multiplier"]

        # 🚫 Hard behavior block
        if not beh.allowed:
            return DecisionResult(
                decision="BLOCK",
                quality_score=0.0,
                risk_pct=risk.final_risk_pct,
                position_size_usd=risk.position_size_usd,
                reasons=beh.reasons + risk.reasons,
                suggested_actions=beh.suggested_actions + [
                    "Switch to paper review mode."
                ],
                market_regime=f"{multi.final_regime} (conf {multi.confidence:.2f})",
                volatility_state=multi.final_volatility,
            )

        # 4️⃣ Strategy fit scoring
        quality_score, fit_reasons = self._strategy_fit_score(
            multi.final_regime,
            multi.final_volatility,
            strategy,
        )

        reasons = fit_reasons + risk.reasons
        suggested = []

        # ⚠️ Low confidence regime
        if multi.confidence < 0.45:
            reasons.append(
                f"Low regime confidence ({multi.confidence:.2f}) → conditions unclear."
            )

            if quality_score < 0.55:
                return DecisionResult(
                    decision="BLOCK",
                    quality_score=quality_score,
                    risk_pct=risk.final_risk_pct,
                    position_size_usd=risk.position_size_usd,
                    reasons=reasons,
                    suggested_actions=[
                        "Wait for clearer market structure.",
                        "Switch timeframe to 15m for confirmation.",
                    ],
                    market_regime=f"{multi.final_regime} (conf {multi.confidence:.2f})",
                    volatility_state=multi.final_volatility,
                )
            else:
                suggested.append(
                    "Proceed only with extra confirmation; consider reducing size."
                )

        # 🚫 Very low quality
        if quality_score < 0.35:
            return DecisionResult(
                decision="BLOCK",
                quality_score=quality_score,
                risk_pct=risk.final_risk_pct,
                position_size_usd=risk.position_size_usd,
                reasons=reasons + ["Trade quality score too low."],
                suggested_actions=[
                    "Wait for a clearer setup.",
                    "Consider changing strategy for the current regime.",
                ],
                market_regime=f"{multi.final_regime} (conf {multi.confidence:.2f})",
                volatility_state=multi.final_volatility,
            )

        # ⚠️ Warn state
        decision = "ALLOW"
        if quality_score < 0.55:
            decision = "WARN"
            suggested.append("Lower position size or wait for confirmation.")

        # 🔥 High volatility
        if multi.final_volatility == "high":
            suggested.append(
                "Use wider stops or smaller size; expect faster swings."
            )

        if not suggested:
            suggested = [
                "Proceed only if your setup matches your plan and stop is respected."
            ]

        return DecisionResult(
            decision=decision,
            quality_score=quality_score,
            risk_pct=risk.final_risk_pct,
            position_size_usd=risk.position_size_usd,
            reasons=reasons,
            suggested_actions=suggested,
            market_regime=f"{multi.final_regime} (conf {multi.confidence:.2f})",
            volatility_state=multi.final_volatility,
        )

    # -------------------------------------------------
    # Strategy fitness model (private)
    # -------------------------------------------------
    def _strategy_fit_score(self, regime: str, volatility: str, strategy: str):
        reasons = []
        score = 1.0

        if strategy.lower() == "breakout" and regime == "RANGE":
            score -= 0.35
            reasons.append("Breakout strategy underperforms in range markets.")

        if volatility == "high":
            score -= 0.15
            reasons.append("High volatility increases false signals.")

        if volatility == "low":
            score -= 0.10
            reasons.append("Low volatility reduces momentum follow-through.")

        return max(score, 0.0), reasons


# # add import
# from .regime_multi import MultiTimeframeRegimeService
# from .risk import RiskService
# from .behavior import BehaviorService


# class DecisionService:
#     def evaluate(self, quality_score: float):
#         if quality_score < 0.5:
#             return {
#                 "status": "WARN",
#                 "recommended_risk": 0.5,
#                 "regime": "RANGE",
#                 "advice": [
#                     "Wait for 15m confirmation",
#                     "Reduce size or skip trade",
#                     "Consider mean-reversion",
#                 ],
#             }

#         return {
#             "status": "OK",
#             "recommended_risk": 1.0,
#             "regime": "TREND",
#             "advice": ["Trade allowed"],
#         }

#     def __init__(self):
#         self.multi_regime = MultiTimeframeRegimeService()
#         self.risk = RiskService()
#         self.behavior = BehaviorService()

#     def check_trade(self, db, candles_by_tf: dict, user_id: str, symbol: str, strategy: str,
#                     account_equity: float, intended_risk_pct: float, stop_distance_pct: float, timeframe: str):

#         beh = self.behavior.check(db, user_id)
#         # Compute multi-tf regime even if blocked (for UI context)
#         per_tf = {tf: self.multi_regime.base.classify(df) for tf, df in candles_by_tf.items()}
#         multi = self.multi_regime.combine(per_tf)

#         risk = self.risk.compute(account_equity, intended_risk_pct, stop_distance_pct, multi.final_volatility)

#         if not beh.allowed:
#             return DecisionResult(
#                 decision="BLOCK",
#                 quality_score=0.0,
#                 risk_pct=risk.final_risk_pct,
#                 position_size_usd=risk.position_size_usd,
#                 reasons=beh.reasons + risk.reasons,
#                 suggested_actions=beh.suggested_actions + ["Switch to paper review mode."],
#                 market_regime=f"{multi.final_regime} (conf {multi.confidence:.2f})",
#                 volatility_state=multi.final_volatility,
#             )

#         quality_score, fit_reasons = self._strategy_fit_score(multi.final_regime, multi.final_volatility, strategy)

#         reasons = fit_reasons + risk.reasons
#         suggested = []

#         # If confidence is low, warn/block earlier
#         if multi.confidence < 0.45:
#             reasons.append(f"Low regime confidence ({multi.confidence:.2f}) → conditions unclear.")
#             if quality_score < 0.55:
#                 return DecisionResult(
#                     decision="BLOCK",
#                     quality_score=quality_score,
#                     risk_pct=risk.final_risk_pct,
#                     position_size_usd=risk.position_size_usd,
#                     reasons=reasons,
#                     suggested_actions=["Wait for clearer market structure.", "Switch timeframe to 15m for confirmation."],
#                     market_regime=f"{multi.final_regime} (conf {multi.confidence:.2f})",
#                     volatility_state=multi.final_volatility,
#                 )
#             else:
#                 suggested.append("Proceed only with extra confirmation; consider reducing size.")

#         if quality_score < 0.35:
#             return DecisionResult(
#                 decision="BLOCK",
#                 quality_score=quality_score,
#                 risk_pct=risk.final_risk_pct,
#                 position_size_usd=risk.position_size_usd,
#                 reasons=reasons + ["Trade quality score too low."],
#                 suggested_actions=["Wait for a clearer setup.", "Consider changing strategy for the current regime."],
#                 market_regime=f"{multi.final_regime} (conf {multi.confidence:.2f})",
#                 volatility_state=multi.final_volatility,
#             )

#         decision = "ALLOW"
#         if quality_score < 0.55:
#             decision = "WARN"
#             suggested.append("Lower position size or wait for confirmation.")

#         if multi.final_volatility == "high":
#             suggested.append("Use wider stops or smaller size; expect faster swings.")

#         if not suggested:
#             suggested = ["Proceed only if your setup matches your plan and stop is respected."]

#         return DecisionResult(
#             decision=decision,
#             quality_score=quality_score,
#             risk_pct=risk.final_risk_pct,
#             position_size_usd=risk.position_size_usd,
#             reasons=reasons,
#             suggested_actions=suggested,
#             market_regime=f"{multi.final_regime} (conf {multi.confidence:.2f})",
#             volatility_state=multi.final_volatility,
#         )


# from dataclasses import dataclass
# from sqlalchemy.orm import Session
# from ..services.regime import RegimeService
# from ..services.risk import RiskService
# from ..services.behavior import BehaviorService
# from ..config import settings


# @dataclass
# class DecisionResult:
#     decision: str
#     quality_score: float
#     risk_pct: float
#     position_size_usd: float
#     reasons: list[str]
#     suggested_actions: list[str]
#     market_regime: str
#     volatility_state: str


# class DecisionService:
#     """
#     Combines:
#     - regime + volatility
#     - risk sizing
#     - behavior guardrails
#     - strategy filter rules (simple MVP)
#     """
#     def __init__(self):
#         self.regime = RegimeService()
#         self.risk = RiskService()
#         self.behavior = BehaviorService()

#     def _strategy_fit_score(self, regime: str, volatility_state: str, strategy: str) -> tuple[float, list[str]]:
#         """
#         Returns a quality score [0..1] and reasons.
#         Very simple heuristic rules for MVP (works surprisingly well for beginners).
#         """
#         s = strategy.lower().strip()
#         reasons = []
#         score = 0.65  # base

#         if regime == "range" and "breakout" in s:
#             score -= 0.35
#             reasons.append("Range regime detected: breakout strategies often fail here.")
#         if regime == "trend" and "mean" in s:
#             score -= 0.25
#             reasons.append("Trend regime detected: mean reversion entries are riskier here.")

#         if volatility_state == "high":
#             score -= 0.10
#             reasons.append("High volatility increases noise and stop-outs for beginners.")

#         score = max(0.0, min(1.0, score))
#         return score, reasons

#     def check_trade(self, db: Session, candles_df, user_id: str, symbol: str, strategy: str,
#                     account_equity: float, intended_risk_pct: float, stop_distance_pct: float, timeframe: str) -> DecisionResult:

#         # Behavior gates first
#         beh = self.behavior.check(db, user_id)
#         if not beh.allowed:
#             # Still compute regime/risk for UI context (optional)
#             reg = self.regime.classify(candles_df)
#             risk = self.risk.compute(account_equity, intended_risk_pct, stop_distance_pct, reg.volatility_state)
#             return DecisionResult(
#                 decision="BLOCK",
#                 quality_score=0.0,
#                 risk_pct=risk.final_risk_pct,
#                 position_size_usd=risk.position_size_usd,
#                 reasons=beh.reasons + risk.reasons,
#                 suggested_actions=beh.suggested_actions + ["Switch to paper review mode."],
#                 market_regime=reg.regime,
#                 volatility_state=reg.volatility_state,
#             )

#         # Market regime
#         reg = self.regime.classify(candles_df)

#         # Risk sizing
#         risk = self.risk.compute(account_equity, intended_risk_pct, stop_distance_pct, reg.volatility_state)

#         # Strategy-fit scoring
#         quality_score, fit_reasons = self._strategy_fit_score(reg.regime, reg.volatility_state, strategy)

#         reasons = []
#         suggested = []

#         reasons += fit_reasons
#         reasons += risk.reasons

#         # Hard blocks
#         if quality_score < 0.35:
#             return DecisionResult(
#                 decision="BLOCK",
#                 quality_score=quality_score,
#                 risk_pct=risk.final_risk_pct,
#                 position_size_usd=risk.position_size_usd,
#                 reasons=reasons + ["Trade quality score too low."],
#                 suggested_actions=["Wait for a clearer setup.", "Consider changing strategy for the current regime."],
#                 market_regime=reg.regime,
#                 volatility_state=reg.volatility_state,
#             )

#         # Soft warnings
#         decision = "ALLOW"
#         if quality_score < 0.55:
#             decision = "WARN"
#             suggested.append("Lower position size or wait for confirmation.")

#         if reg.volatility_state == "high":
#             suggested.append("Use wider stops or smaller size; expect faster swings.")

#         if not suggested:
#             suggested = ["Proceed only if your setup matches your plan and stop is respected."]

#         return DecisionResult(
#             decision=decision,
#             quality_score=quality_score,
#             risk_pct=risk.final_risk_pct,
#             position_size_usd=risk.position_size_usd,
#             reasons=reasons,
#             suggested_actions=suggested,
#             market_regime=reg.regime,
#             volatility_state=reg.volatility_state,
#         )
