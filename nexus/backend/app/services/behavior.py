from dataclasses import dataclass
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..config import settings
from ..models import DailyStat, Trade


@dataclass
class BehaviorResult:
    allowed: bool
    reasons: list[str]
    suggested_actions: list[str]
    cooldown_until: datetime | None


class BehaviorService:
    """
    Beginner behavior guardrails:
    - max trades per day
    - cooldown after 2 consecutive losses
    - respect cooldown_until if set
    """
    def get_or_create_daily(self, db: Session, user_id: str, day: date) -> DailyStat:
        stmt = select(DailyStat).where(DailyStat.user_id == user_id, DailyStat.day == day)
        row = db.execute(stmt).scalar_one_or_none()
        if row:
            return row
        ds = DailyStat(user_id=user_id, day=day)
        db.add(ds)
        db.commit()
        db.refresh(ds)
        return ds

    def check(self, db: Session, user_id: str) -> BehaviorResult:
        reasons: list[str] = []
        suggested: list[str] = []
        now = datetime.utcnow()
        today = now.date()

        ds = self.get_or_create_daily(db, user_id, today)

        if ds.cooldown_until and now < ds.cooldown_until:
            reasons.append(f"Cooldown active until {ds.cooldown_until.isoformat()}Z.")
            suggested.append("Wait out the cooldown. Review last two trades.")
            return BehaviorResult(allowed=False, reasons=reasons, suggested_actions=suggested, cooldown_until=ds.cooldown_until)

        if ds.trades_count >= settings.max_trades_per_day:
            reasons.append(f"Max trades/day reached ({ds.trades_count}/{settings.max_trades_per_day}).")
            suggested.append("Stop trading for today. Review performance.")
            return BehaviorResult(allowed=False, reasons=reasons, suggested_actions=suggested, cooldown_until=None)

        return BehaviorResult(allowed=True, reasons=[], suggested_actions=[], cooldown_until=None)

    def update_on_trade_close(self, db: Session, user_id: str, pnl: float):
        now = datetime.utcnow()
        today = now.date()
        ds = self.get_or_create_daily(db, user_id, today)

        # Update counts
        ds.trades_count += 1
        ds.realized_pnl += float(pnl)

        if pnl > 0:
            ds.wins += 1
            ds.consecutive_losses = 0
        else:
            ds.losses += 1
            ds.consecutive_losses += 1

        # Apply cooldown after 2 consecutive losses
        if ds.consecutive_losses >= 2:
            ds.cooldown_until = now + timedelta(minutes=settings.cooldown_minutes_after_two_losses)

        db.add(ds)
        db.commit()
