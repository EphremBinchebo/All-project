import requests
import pandas as pd
from dataclasses import dataclass

BINANCE_BASE = "https://api.binance.com"

@dataclass
class Candles:
    df: pd.DataFrame  # columns: ["ts","open","high","low","close","volume"]

class BinanceMarketDataService:
    """
    Uses Binance public REST API for spot klines (candles).
    No API key required.
    """

    def get_candles(self, symbol: str, timeframe: str = "1m", limit: int = 300) -> Candles:
        url = f"{BINANCE_BASE}/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": timeframe,
            "limit": limit
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        # Binance kline format:
        # [
        #   0 open_time, 1 open, 2 high, 3 low, 4 close, 5 volume,
        #   6 close_time, ...
        # ]
        df = pd.DataFrame(data, columns=[
            "open_time","open","high","low","close","volume",
            "close_time","qav","num_trades","tbbav","tbqav","ignore"
        ])

        df = df[["open_time","open","high","low","close","volume"]]
        df["ts"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df = df.drop(columns=["open_time"])

        # Cast to float
        for c in ["open","high","low","close","volume"]:
            df[c] = df[c].astype(float)

        return Candles(df=df.reset_index(drop=True))


# from dataclasses import dataclass
# import numpy as np
# import pandas as pd

# """
# MVP NOTE:
# - For now, we generate synthetic candles if you don't connect a real feed.
# - Replace `get_candles()` with Binance/Bybit/TradingView data later.
# """

# @dataclass
# class Candles:
#     df: pd.DataFrame  # columns: ["ts","open","high","low","close","volume"]


# class MarketDataService:
#     def get_candles(self, symbol: str, timeframe: str = "1m", limit: int = 300) -> Candles:
#         # Synthetic fallback (random walk). Replace with real exchange data when ready.
#         rng = np.random.default_rng(7)
#         rets = rng.normal(loc=0.0, scale=0.0015, size=limit)
#         price = 100.0 * np.exp(np.cumsum(rets))
#         df = pd.DataFrame({
#             "ts": pd.date_range(end=pd.Timestamp.utcnow(), periods=limit, freq="min"),
#             "open": price,
#             "high": price * (1 + rng.uniform(0, 0.001, size=limit)),
#             "low":  price * (1 - rng.uniform(0, 0.001, size=limit)),
#             "close": price * (1 + rng.normal(0, 0.0005, size=limit)),
#             "volume": rng.uniform(10, 100, size=limit),
#         })
#         return Candles(df=df)
