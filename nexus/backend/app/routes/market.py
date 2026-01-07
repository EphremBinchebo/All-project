from fastapi import APIRouter, HTTPException, Query
import httpx

router = APIRouter(prefix="/api/market", tags=["Market"])


@router.get("/candles")
async def get_candles(
    symbol: str = Query("BTCUSD"),  # Coinbase format
    interval: int = Query(300),     # Coinbase granularity in seconds
    limit: int = Query(200, le=500),
):
    """
    Fetch candles from Coinbase public API:
    https://api.exchange.coinbase.com/products/{symbol}/candles
    """

    # Coinbase expects uppercase with hyphen
    # Typical mapping: BTCUSDT -> BTC-USD
    pair = symbol.replace("USDT", "-USD").replace("USD", "-USD")
    
    url = f"https://api.exchange.coinbase.com/products/{pair}/candles"
    params = {"granularity": interval}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, params=params)
            res.raise_for_status()
            raw = res.json()

        if not isinstance(raw, list):
            raise HTTPException(status_code=502, detail="Invalid market response")

        # Coinbase returns: [ time, low, high, open, close, volume ]
        candles = []
        for c in raw[:limit]:
            candles.append(
                {
                    "time": int(c[0]),   # UTC seconds
                    "open": float(c[3]),
                    "high": float(c[2]),
                    "low": float(c[1]),
                    "close": float(c[4]),
                }
            )

        # Coinbase API returns newest first, reverse for chart
        candles.reverse()

        return candles

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Market datasource error")
    except Exception as e:
        print("🔥 MARKET ROUTE ERROR:", repr(e))
        raise HTTPException(status_code=500, detail="Market data unavailable")


# import httpx
# from fastapi import APIRouter, HTTPException

# router = APIRouter(prefix="/api/market", tags=["Market"])


# @router.get("/candles")
# async def get_candles(
#     symbol: str = "BTCUSDT",
#     interval: str = "5m",
#     limit: int = 200,
# ):
#     try:
#         url = (
#             "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
#             "?vs_currency=usd&days=1&interval=minute"
#         )

#         headers = {
#             "Accept": "application/json",
#             "User-Agent": "Nexus-AI-Trading/1.0 (contact: dev@nexus.ai)",
#         }

#         async with httpx.AsyncClient(timeout=15) as client:
#             resp = await client.get(url, headers=headers)
#             resp.raise_for_status()

#         data = resp.json()

#         prices = data.get("prices", [])
#         if not prices:
#             raise ValueError("Empty price data")

#         candles = []
#         for i in range(1, len(prices)):
#             candles.append({
#                 "time": int(prices[i][0] / 1000),
#                 "open": prices[i-1][1],
#                 "high": max(prices[i-1][1], prices[i][1]),
#                 "low": min(prices[i-1][1], prices[i][1]),
#                 "close": prices[i][1],
#             })

#         return candles[-limit:]

#     except Exception as e:
#         print("🔥 MARKET ROUTE ERROR:", repr(e))
#         raise HTTPException(status_code=500, detail="Market data unavailable")


# from fastapi import APIRouter, HTTPException, Query
# import httpx

# router = APIRouter(prefix="/api/market", tags=["Market"])


# @router.get("/candles")
# async def get_candles(
#     symbol: str = Query("BTCUSDT"),
#     interval: str = Query("5m"),
#     limit: int = Query(200, le=500),
# ):
#     """
#     Fetch OHLCV candles from CoinGecko (safe alternative to Binance)
#     """

#     # CoinGecko uses different symbols & structure
#     # We'll simulate candles using market_chart (simplified MVP)
#     url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"

#     params = {
#         "vs_currency": "usd",
#         "days": "1",
#         "interval": "minute",
#     }

#     try:
#         async with httpx.AsyncClient(timeout=10) as client:
#             resp = await client.get(url, params=params)
#             resp.raise_for_status()
#             data = resp.json()

#         prices = data.get("prices", [])

#         if not prices:
#             raise HTTPException(status_code=502, detail="No market data")

#         candles = []
#         for i in range(len(prices) - 1):
#             t = prices[i][0] // 1000
#             o = prices[i][1]
#             c = prices[i + 1][1]
#             h = max(o, c)
#             l = min(o, c)

#             candles.append(
#                 {
#                     "time": t,
#                     "open": o,
#                     "high": h,
#                     "low": l,
#                     "close": c,
#                 }
#             )

#         return candles[-limit:]

#     except Exception as e:
#         print("🔥 MARKET ROUTE ERROR:", repr(e))
#         raise HTTPException(status_code=500, detail="Market data unavailable")


# from typing import List
# from fastapi import APIRouter, HTTPException, Query
# import httpx
# from datetime import datetime, timezone


# router = APIRouter(prefix="/api/market", tags=["market"])

# # Mapping symbols → CoinGecko IDs
# COINGECKO_IDS = {
#     "BTCUSDT": "bitcoin",
#     "ETHUSDT": "ethereum",
# }

# router = APIRouter(prefix="/api/market", tags=["Market"])

# @router.get("/candles")
# def candles(symbol: str = "BTCUSDT", interval: str = "5m", limit: int = 200):
#     # Demo-safe candles to prevent frontend crashes
#     return [
#         {
#             "time": "2024-01-01",
#             "open": 42000,
#             "high": 42500,
#             "low": 41800,
#             "close": 42300
#         },
#         {
#             "time": "2024-01-02",
#             "open": 42300,
#             "high": 43000,
#             "low": 42000,
#             "close": 42800
#         }
#     ]

# # @router.get("/candles")
# # async def get_candles(
# #     symbol: str = Query("BTCUSDT"),
# #     interval: str = Query("5m"),
# #     limit: int = Query(200, ge=1, le=500),
# # ) -> List[dict]:
# #     """
# #     Returns candles in lightweight-charts format:
# #     [
# #       { time, open, high, low, close }
# #     ]
# #     """

#     coin_id = COINGECKO_IDS.get(symbol)
#     if not coin_id:
#         raise HTTPException(status_code=400, detail="Unsupported symbol")

#     # CoinGecko granularity workaround
#     # We fetch minute data and trim
#     url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
#     params = {"vs_currency": "usd", "days": 1}

#     try:
#         async with httpx.AsyncClient(timeout=10) as client:
#             res = await client.get(url, params=params)
#             res.raise_for_status()
#             raw = res.json()

#         if not isinstance(raw, list):
#             raise HTTPException(status_code=502, detail="Unexpected market response")

#         candles = []
#         for item in raw[-limit:]:
#             # [ timestamp(ms), open, high, low, close ]
#             candles.append(
#                 {
#                     "time": int(item[0] / 1000),  # UNIX seconds
#                     "open": float(item[1]),
#                     "high": float(item[2]),
#                     "low": float(item[3]),
#                     "close": float(item[4]),
#                 }
#             )

#         return candles

#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=502, detail="Market upstream error")
#     except Exception as e:
#         raise HTTPException(status_code=503, detail="Market data unavailable")

# from fastapi import APIRouter, HTTPException
# import requests
# from datetime import datetime

# router = APIRouter(prefix="/api/market", tags=["Market"])

# @router.get("/candles")
# def get_candles(
#     symbol: str = "BTCUSDT",
#     interval: str = "5m",
#     limit: int = 200
# ):
#     """
#     Returns candles in lightweight-charts format
#     """
#     url = "https://api.binance.com/api/v3/klines"
#     params = {
#         "symbol": symbol,
#         "interval": interval,
#         "limit": limit,
#     }

#     try:
#         res = requests.get(url, params=params, timeout=10)
#         res.raise_for_status()
#         raw = res.json()
#     except Exception as e:
#         print("🔥 MARKET ROUTE ERROR:", repr(e))
#         raise HTTPException(status_code=500, detail=str(e))
#     # except Exception:
#     #     raise HTTPException(status_code=500, detail="Market data unavailable")

#     candles = []
#     for k in raw:
#         candles.append({
#             "time": int(k[0] / 1000),  # UNIX seconds ✅
#             "open": float(k[1]),
#             "high": float(k[2]),
#             "low": float(k[3]),
#             "close": float(k[4]),
#         })

#     return candles


# from fastapi import APIRouter
# import requests

# router = APIRouter(prefix="/api/market", tags=["Market"])

# @router.get("/candles")
# def get_candles(
#     symbol: str = "BTCUSDT",
#     interval: str = "5m",
#     limit: int = 200,
# ):
#     url = "https://api.binance.com/api/v3/klines"
#     params = {
#         "symbol": symbol,
#         "interval": interval,
#         "limit": limit,
#     }

#     r = requests.get(url, params=params, timeout=10)
#     r.raise_for_status()

#     data = r.json()

#     candles = [
#         {
#             "time": int(c[0] / 1000),
#             "open": float(c[1]),
#             "high": float(c[2]),
#             "low": float(c[3]),
#             "close": float(c[4]),
#         }
#         for c in data
#     ]

#     return candles


# from fastapi import APIRouter, HTTPException
# import httpx
# import traceback

# router = APIRouter(prefix="/api/market", tags=["market"])

# # Use Coinbase FIRST (most reliable, no geo blocking)
# COINBASE_URL = "https://api.exchange.coinbase.com/products/BTC-USD/candles"


# @router.get("/candles")
# async def get_candles(limit: int = 200):
#     print("✅ /api/market/candles called")

#     try:
#         async with httpx.AsyncClient(timeout=10) as client:
#             r = await client.get(
#                 COINBASE_URL,
#                 params={"granularity": 300},  # 5 minutes
#                 headers={"Accept": "application/json"},
#             )

#         print("🔎 Coinbase status:", r.status_code)

#         if r.status_code != 200:
#             print("❌ Coinbase response:", r.text)
#             raise HTTPException(502, "Coinbase API error")

#         raw = r.json()
#         print("📦 Raw candle count:", len(raw))

#         candles = []
#         for c in raw[:limit]:
#             candles.append(
#                 {
#                     "time": int(c[0]),
#                     "open": float(c[3]),
#                     "high": float(c[2]),
#                     "low": float(c[1]),
#                     "close": float(c[4]),
#                 }
#             )

#         candles = sorted(candles, key=lambda x: x["time"])

#         print("✅ Returning candles:", len(candles))
#         return candles

#     except Exception as e:
#         print("🔥 MARKET ROUTE FAILED")
#         traceback.print_exc()
#         # 🚨 NEVER return {} — ALWAYS raise
#         raise HTTPException(
#             status_code=500,
#             detail=str(e),
#         )

# from fastapi import APIRouter, HTTPException
# import httpx

# router = APIRouter(prefix="/api/market", tags=["market"])

# BINANCE_URL = "https://api.binance.com/api/v3/klines"


# @router.get("/candles")
# async def get_candles(
#     symbol: str = "BTCUSDT",
#     interval: str = "5m",
#     limit: int = 200,
# ):
#     try:
#         async with httpx.AsyncClient(timeout=10) as client:
#             r = await client.get(
#                 BINANCE_URL,
#                 params={
#                     "symbol": symbol,
#                     "interval": interval,
#                     "limit": limit,
#                 },
#             )

#             # 👇 THIS IS CRITICAL
#             if r.status_code != 200:
#                 raise HTTPException(
#                     status_code=502,
#                     detail=f"Binance error {r.status_code}",
#                 )

#             raw = r.json()

#         if not isinstance(raw, list):
#             raise HTTPException(
#                 status_code=500,
#                 detail="Unexpected Binance response format",
#             )

#         candles = []
#         for c in raw:
#             candles.append(
#                 {
#                     "time": int(c[0] / 1000),
#                     "open": float(c[1]),
#                     "high": float(c[2]),
#                     "low": float(c[3]),
#                     "close": float(c[4]),
#                 }
#             )

#         return candles

#     except httpx.RequestError as e:
#         raise HTTPException(
#             status_code=503,
#             detail=f"Network error contacting Binance: {e}",
#         )

#     except Exception as e:
#         # 🔥 DO NOT SILENCE ERRORS
#         raise HTTPException(
#             status_code=500,
#             detail=f"Market data failure: {str(e)}",
#         )


# # app/routes/market.py
# from fastapi import APIRouter, HTTPException
# import httpx
# from datetime import datetime

# router = APIRouter(prefix="/api/market", tags=["Market"])

# BINANCE_BASE = "https://api.binance.com/api/v3/klines"


# @router.get("/candles")
# async def get_candles(
#     symbol: str = "BTCUSDT",
#     interval: str = "5m",
#     limit: int = 200,
# ):
#     """
#     Returns candlestick data formatted for Lightweight Charts
#     """
#     params = {
#         "symbol": symbol,
#         "interval": interval,
#         "limit": limit,
#     }

#     try:
#         async with httpx.AsyncClient(timeout=10) as client:
#             resp = await client.get(BINANCE_BASE, params=params)
#             resp.raise_for_status()
#             raw = resp.json()

#         candles = []
#         for c in raw:
#             candles.append(
#                 {
#                     "time": int(c[0] / 1000),  # seconds (NOT ms)
#                     "open": float(c[1]),
#                     "high": float(c[2]),
#                     "low": float(c[3]),
#                     "close": float(c[4]),
#                 }
#             )

#         return candles

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Market data unavailable: {e}")


# from fastapi import APIRouter, HTTPException, Query
# import httpx
# from datetime import datetime

# router = APIRouter(prefix="/api/market", tags=["market"])

# BINANCE_URL = "https://api.binance.com/api/v3/klines"


# @router.get("/candles")
# async def get_candles(
#     symbol: str = Query("BTCUSDT"),
#     interval: str = Query("5m"),
#     limit: int = Query(200),
# ):
#     try:
#         async with httpx.AsyncClient(timeout=10) as client:
#             r = await client.get(
#                 BINANCE_URL,
#                 params={
#                     "symbol": symbol,
#                     "interval": interval,
#                     "limit": limit,
#                 },
#             )
#             r.raise_for_status()
#             raw = r.json()

#         candles = [
#             {
#                 "time": int(c[0] / 1000),  # seconds (Lightweight Charts requirement)
#                 "open": float(c[1]),
#                 "high": float(c[2]),
#                 "low": float(c[3]),
#                 "close": float(c[4]),
#             }
#             for c in raw
#         ]

#         return candles

#     except Exception as e:
#         raise HTTPException(status_code=503, detail="Market data unavailable")

# from fastapi import APIRouter, HTTPException
# import httpx
# router = APIRouter(prefix="/api/market", tags=["market"])

# BINANCE_REST = "https://api.binance.com/api/v3/klines"

# @router.get("/candles")
# async def get_candles(
#     symbol: str = "BTCUSDT",
#     interval: str = "5m",
#     limit: int = 200,
# ):
#     try:
#         async with httpx.AsyncClient(timeout=10) as client:
#             res = await client.get(
#                 BINANCE_REST,
#                 params={
#                     "symbol": symbol,
#                     "interval": interval,
#                     "limit": limit,
#                 },
#             )
#             res.raise_for_status()
#             data = res.json()

#         # Convert Binance format → Lightweight Charts format
#         candles = [
#             {
#                 "time": int(c[0] / 1000),
#                 "open": float(c[1]),
#                 "high": float(c[2]),
#                 "low": float(c[3]),
#                 "close": float(c[4]),
#             }
#             for c in data
#         ]

#         return candles

#     except Exception as e:
#         raise HTTPException(status_code=500, detail="Market data unavailable")
