# Nexus Trading Backend (MVP)

## 1) Create venv and install
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

## 2) Run server
uvicorn app.main:app --reload --port 8000

## 3) Test endpoints
Open:
- http://127.0.0.1:8000/docs

### Example: check trade
POST /api/nexus/check-trade
{
  "user_id": "11111111-1111-1111-1111-111111111111",
  "symbol": "BTCUSDT",
  "strategy": "breakout",
  "account_equity": 1000,
  "intended_risk_pct": 1.0,
  "stop_distance_pct": 0.5,
  "timeframe": "1m"
}

### Example: open trade
POST /api/trades/open
{
  "user_id": "11111111-1111-1111-1111-111111111111",
  "symbol": "BTCUSDT",
  "strategy": "mean_reversion",
  "entry_price": 43000,
  "qty": 0.01,
  "risk_pct": 1.0,
  "stop_distance_pct": 0.5,
  "mode": "PAPER",
  "notes": "paper trade"
}

### Example: close trade
POST /api/trades/close
{
  "user_id": "11111111-1111-1111-1111-111111111111",
  "trade_id": "<trade-id-from-open>",
  "exit_price": 43100,
  "pnl": 10.5,
  "rr": 1.2,
  "rule_violation": false,
  "notes": "closed"
}
