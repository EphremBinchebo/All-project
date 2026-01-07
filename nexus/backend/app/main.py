from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from .config import settings
from .db import Base, engine, get_db
from .models import Trade, DailyStat, User
from fastapi.middleware.cors import CORSMiddleware
# from app.routes.market import router as market_router
# from fastapi.middleware.cors import CORSMiddleware
from app.routes.market import router as market_router
from app.routes.session import router as session_router



from .schemas import (
    CheckTradeRequest,
    CheckTradeResponse,
    TradeOpenRequest,
    TradeCloseRequest,
    TradeOut,
    DailyReport,
    WeeklyReport,
    RegisterRequest,
    LoginRequest,
    TokenResponse,
)
from .services.market_data_binance import BinanceMarketDataService
from .services.decision import DecisionService
from .services.behavior import BehaviorService
from .services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)


# -------------------------------------------------
# App & DB Initialization
# -------------------------------------------------

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Nexus AI Trading Backend (Crypto – Paper Trading MVP)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router)

market = BinanceMarketDataService()
decision_svc = DecisionService()
behavior_svc = BehaviorService()

# app.include_router(auth_router)
# app.include_router(trade_router)
# app.include_router(market_router)


# -------------------------------------------------
# Health
# -------------------------------------------------

# @app.get("/health")
# def health():
#     return {"status": "ok", "app": settings.app_name}

# -------------------------------------------------
# AI Decision Engine
# -------------------------------------------------

@app.post("/api/nexus/check-trade", response_model=CheckTradeResponse)
def check_trade(
    req: CheckTradeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Pull candles
    candles_by_tf = {
        "1m": market.get_candles(req.symbol, "1m", limit=300).df,
        "5m": market.get_candles(req.symbol, "5m", limit=300).df,
        "15m": market.get_candles(req.symbol, "15m", limit=300).df,
    }

    # Ask Nexus decision service
    res = decision_svc.check_trade(
        db=db,
        candles_by_tf=candles_by_tf,
        user_id=user.id,
        symbol=req.symbol,
        strategy=req.strategy,
        account_equity=req.account_equity,
        intended_risk_pct=req.intended_risk_pct,
        stop_distance_pct=req.stop_distance_pct,
        timeframe=req.timeframe,
    )

    return CheckTradeResponse(
        decision=res.decision,
        quality_score=res.quality_score,
        risk_pct=res.risk_pct,
        position_size_usd=res.position_size_usd,
        reasons=res.reasons,
        suggested_actions=res.suggested_actions,
        market_regime=res.market_regime,
        volatility_state=res.volatility_state,
    )

# -------------------------------------------------
# Trades
# -------------------------------------------------

@app.post("/api/trades/open", response_model=TradeOut)
def open_trade(
    req: TradeOpenRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if req.mode != "PAPER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PAPER mode is supported in MVP.",
        )

    trade = Trade(
        user_id=user.id,
        symbol=req.symbol,
        strategy=req.strategy,
        entry_price=req.entry_price,
        qty=req.qty,
        risk_pct=req.risk_pct,
        stop_distance_pct=req.stop_distance_pct,
        mode=req.mode,
        status="OPEN",
        notes=req.notes,
    )

    db.add(trade)
    db.commit()
    db.refresh(trade)

    # IMPORTANT: returning SQLAlchemy model is OK only if TradeOut uses from_attributes=True
    return trade


@app.post("/api/trades/close", response_model=TradeOut)
def close_trade(
    req: TradeCloseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    trade = db.execute(
        select(Trade).where(
            Trade.id == req.trade_id,
            Trade.user_id == user.id,
        )
    ).scalar_one_or_none()

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found.")

    if trade.status != "OPEN":
        raise HTTPException(status_code=400, detail="Trade is not OPEN.")

    trade.exit_price = req.exit_price
    trade.closed_at = datetime.utcnow()
    trade.status = "CLOSED"
    trade.pnl = req.pnl
    trade.rr = req.rr
    trade.rule_violation = req.rule_violation

    if req.notes:
        trade.notes = (trade.notes or "") + f"\n{req.notes}"

    db.commit()
    db.refresh(trade)

    behavior_svc.update_on_trade_close(db, user.id, req.pnl)
    return trade


@app.get("/api/trades", response_model=List[TradeOut])
def list_trades(
    days: int = 7,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)

    trades = db.execute(
        select(Trade)
        .where(
            Trade.user_id == user.id,
            Trade.opened_at >= since,
        )
        .order_by(Trade.opened_at.desc())
    ).scalars().all()

    return trades

# -------------------------------------------------
# Reports
# -------------------------------------------------

@app.get("/api/reports/daily", response_model=DailyReport)
def daily_report(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = datetime.utcnow().date()
    ds = behavior_svc.get_or_create_daily(db, user.id, today)

    return DailyReport(
        day=str(ds.day),
        trades=ds.trades_count,
        wins=ds.wins,
        losses=ds.losses,
        realized_pnl=ds.realized_pnl,
        consecutive_losses=ds.consecutive_losses,
        cooldown_until=ds.cooldown_until.isoformat() + "Z" if ds.cooldown_until else None,
    )


@app.get("/api/reports/weekly", response_model=WeeklyReport)
def weekly_report(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    end_day = datetime.utcnow().date()
    start_day = end_day - timedelta(days=6)

    rows = db.execute(
        select(DailyStat)
        .where(
            DailyStat.user_id == user.id,
            DailyStat.day.between(start_day, end_day),
        )
        .order_by(DailyStat.day.asc())
    ).scalars().all()

    return WeeklyReport(
        start_day=str(start_day),
        end_day=str(end_day),
        trades=sum(r.trades_count for r in rows),
        wins=sum(r.wins for r in rows),
        losses=sum(r.losses for r in rows),
        realized_pnl=float(sum(r.realized_pnl for r in rows)),
        max_consecutive_losses=max((r.consecutive_losses for r in rows), default=0),
    )

# -------------------------------------------------
# Authentication
# -------------------------------------------------

@app.post("/api/auth/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()

    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(email=email, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.market import router as market_router

app = FastAPI(title="Nexus Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router)
app.include_router(session_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    return TokenResponse(access_token=create_access_token(user.id))


# from datetime import datetime, timedelta
# from typing import List

# from fastapi import Depends
# from .db import get_db


# from fastapi import FastAPI, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from sqlalchemy import select

# from .config import settings
# from .db import Base, engine, get_db
# from .models import Trade, DailyStat, User
# from .schemas import (
#     CheckTradeRequest,
#     CheckTradeResponse,
#     TradeOpenRequest,
#     TradeCloseRequest,
#     TradeOut,
#     DailyReport,
#     WeeklyReport,
#     RegisterRequest,
#     LoginRequest,
#     TokenResponse,
# )
# from .services.market_data_binance import BinanceMarketDataService
# from .services.decision import DecisionService
# from .services.behavior import BehaviorService
# from .services.auth import (
#     hash_password,
#     verify_password,
#     create_access_token,
#     get_current_user,
# )

# # -------------------------------------------------
# # App & DB Initialization
# # -------------------------------------------------

# Base.metadata.create_all(bind=engine)

# app = FastAPI(
#     title=settings.app_name,
#     version="0.1.0",
#     description="Nexus AI Trading Backend (Crypto – Paper Trading MVP)",
# )

# market = BinanceMarketDataService()
# decision_svc = DecisionService()
# behavior_svc = BehaviorService()

# # -------------------------------------------------
# # Health
# # -------------------------------------------------

# @app.get("/health")
# def health():
#     return {"status": "ok", "app": settings.app_name}

# # -------------------------------------------------
# # AI Decision Engine
# # -------------------------------------------------

# # @app.post("/api/nexus/check-trade", response_model=CheckTradeResponse)
# # def check_trade(
# #     req: CheckTradeRequest,
# #     db: Session = Depends(get_db),
# #     user: User = Depends(get_current_user),
# # ):

# @app.post("/api/nexus/check-trade", response_model=CheckTradeResponse)
# def check_trade(
#     payload: CheckTradeRequest,
#     db: Session = Depends(get_db),   # ✅ correct
# ):
# # @app.post("/api/nexus/check-trade", response_model=CheckTradeResponse)
# # def check_trade(
# #     payload: CheckTradeRequest,
# #     db: Session = Depends(get_db),
# # ):
#     decision = decision_svc.evaluate(payload, db)
#     candles_by_tf = {
#         "1m": market.get_candles(req.symbol, "1m", limit=300).df,
#         "5m": market.get_candles(req.symbol, "5m", limit=300).df,
#         "15m": market.get_candles(req.symbol, "15m", limit=300).df,
#     }

#     res = decision_svc.check_trade(
#         db=db,
#         candles_by_tf=candles_by_tf,
#         user_id=user.id,
#         symbol=req.symbol,
#         strategy=req.strategy,
#         account_equity=req.account_equity,
#         intended_risk_pct=req.intended_risk_pct,
#         stop_distance_pct=req.stop_distance_pct,
#         timeframe=req.timeframe,
#     )

#     return CheckTradeResponse(
#         decision=res.decision,
#         quality_score=res.quality_score,
#         risk_pct=res.risk_pct,
#         position_size_usd=res.position_size_usd,
#         reasons=res.reasons,
#         suggested_actions=res.suggested_actions,
#         market_regime=res.market_regime,
#         volatility_state=res.volatility_state,
#     )

# # -------------------------------------------------
# # Trades
# # -------------------------------------------------

# @app.post("/api/trades/open", response_model=TradeOut)
# def open_trade(
#     req: TradeOpenRequest,
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user),
# ):
#     if req.mode != "PAPER":
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Only PAPER mode is supported in MVP.",
#         )

#     trade = Trade(
#         user_id=user.id,
#         symbol=req.symbol,
#         strategy=req.strategy,
#         entry_price=req.entry_price,
#         qty=req.qty,
#         risk_pct=req.risk_pct,
#         stop_distance_pct=req.stop_distance_pct,
#         mode=req.mode,
#         status="OPEN",
#         notes=req.notes,
#     )

#     db.add(trade)
#     db.commit()
#     db.refresh(trade)
#     return trade


# @app.post("/api/trades/close", response_model=TradeOut)
# def close_trade(
#     req: TradeCloseRequest,
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user),
# ):
#     trade = db.execute(
#         select(Trade).where(
#             Trade.id == req.trade_id,
#             Trade.user_id == user.id,
#         )
#     ).scalar_one_or_none()

#     if not trade:
#         raise HTTPException(status_code=404, detail="Trade not found.")

#     if trade.status != "OPEN":
#         raise HTTPException(status_code=400, detail="Trade is not OPEN.")

#     trade.exit_price = req.exit_price
#     trade.closed_at = datetime.utcnow()
#     trade.status = "CLOSED"
#     trade.pnl = req.pnl
#     trade.rr = req.rr
#     trade.rule_violation = req.rule_violation

#     if req.notes:
#         trade.notes = (trade.notes or "") + f"\n{req.notes}"

#     db.commit()
#     db.refresh(trade)

#     behavior_svc.update_on_trade_close(db, user.id, req.pnl)

#     return trade


# @app.get("/api/trades", response_model=List[TradeOut])
# def list_trades(
#     days: int = 7,
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user),
# ):
#     since = datetime.utcnow() - timedelta(days=days)

#     trades = db.execute(
#         select(Trade)
#         .where(
#             Trade.user_id == user.id,
#             Trade.opened_at >= since,
#         )
#         .order_by(Trade.opened_at.desc())
#     ).scalars().all()

#     return trades

# # -------------------------------------------------
# # Reports
# # -------------------------------------------------

# @app.get("/api/reports/daily", response_model=DailyReport)
# def daily_report(
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user),
# ):
#     today = datetime.utcnow().date()
#     ds = behavior_svc.get_or_create_daily(db, user.id, today)

#     return DailyReport(
#         day=str(ds.day),
#         trades=ds.trades_count,
#         wins=ds.wins,
#         losses=ds.losses,
#         realized_pnl=ds.realized_pnl,
#         consecutive_losses=ds.consecutive_losses,
#         cooldown_until=ds.cooldown_until.isoformat() + "Z"
#         if ds.cooldown_until
#         else None,
#     )


# @app.get("/api/reports/weekly", response_model=WeeklyReport)
# def weekly_report(
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user),
# ):
#     end_day = datetime.utcnow().date()
#     start_day = end_day - timedelta(days=6)

#     rows = db.execute(
#         select(DailyStat)
#         .where(
#             DailyStat.user_id == user.id,
#             DailyStat.day.between(start_day, end_day),
#         )
#         .order_by(DailyStat.day.asc())
#     ).scalars().all()

#     return WeeklyReport(
#         start_day=str(start_day),
#         end_day=str(end_day),
#         trades=sum(r.trades_count for r in rows),
#         wins=sum(r.wins for r in rows),
#         losses=sum(r.losses for r in rows),
#         realized_pnl=float(sum(r.realized_pnl for r in rows)),
#         max_consecutive_losses=max(
#             (r.consecutive_losses for r in rows), default=0
#         ),
#     )

# # -------------------------------------------------
# # Authentication
# # -------------------------------------------------

# @app.post("/api/auth/register", response_model=TokenResponse)
# def register(req: RegisterRequest, db: Session = Depends(get_db)):
#     email = req.email.strip().lower()

#     if len(req.password) < 8:
#         raise HTTPException(
#             status_code=400,
#             detail="Password must be at least 8 characters.",
#         )

#     if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
#         raise HTTPException(status_code=400, detail="Email already registered.")

#     user = User(
#         email=email,
#         password_hash=hash_password(req.password),
#     )
#     db.add(user)
#     db.commit()
#     db.refresh(user)

#     return TokenResponse(access_token=create_access_token(user.id))


# @app.post("/api/auth/login", response_model=TokenResponse)
# def login(req: LoginRequest, db: Session = Depends(get_db)):
#     email = req.email.strip().lower()

#     user = db.execute(
#         select(User).where(User.email == email)
#     ).scalar_one_or_none()

#     if not user or not verify_password(req.password, user.password_hash):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid credentials.",
#         )

#     return TokenResponse(access_token=create_access_token(user.id))
