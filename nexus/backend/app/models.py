import uuid
from datetime import datetime, date

from sqlalchemy import (
    String,
    DateTime,
    Float,
    Integer,
    Boolean,
    Date,
    Index,
    UniqueConstraint,
)

from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


# -------------------------------------------------
# Trades
# -------------------------------------------------

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id: Mapped[str] = mapped_column(String(36), index=True)

    symbol: Mapped[str] = mapped_column(String(32), index=True)
    strategy: Mapped[str] = mapped_column(String(64), default="unknown")

    mode: Mapped[str] = mapped_column(
        String(16),
        default="PAPER",  # PAPER or LIVE (LIVE disabled for MVP)
    )

    status: Mapped[str] = mapped_column(
        String(16),
        default="OPEN",  # OPEN / CLOSED
    )

    opened_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    entry_price: Mapped[float] = mapped_column(Float, default=0.0)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    qty: Mapped[float] = mapped_column(Float, default=0.0)

    risk_pct: Mapped[float] = mapped_column(Float, default=0.0)
    stop_distance_pct: Mapped[float] = mapped_column(Float, default=0.0)

    pnl: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Realized PnL in quote currency",
    )

    rr: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Risk/Reward multiple",
    )

    rule_violation: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)


Index(
    "ix_trades_user_day",
    Trade.user_id,
    Trade.opened_at,
)


# -------------------------------------------------
# Daily Stats (Behavior / Risk Control)
# -------------------------------------------------

class DailyStat(Base):
    __tablename__ = "daily_stats"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id: Mapped[str] = mapped_column(String(36), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)

    trades_count: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)

    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)

    cooldown_until: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


# -------------------------------------------------
# Users
# -------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    email: Mapped[str] = mapped_column(String(255), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )
