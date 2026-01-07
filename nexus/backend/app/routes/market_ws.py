from fastapi import APIRouter, WebSocket
import asyncio
import json
import websockets

router = APIRouter()

BINANCE_WS = "wss://stream.binance.com:9443/ws/btcusdt@kline_5m"

@router.websocket("/ws/market")
async def market_ws(websocket: WebSocket):
    await websocket.accept()

    async with websockets.connect(BINANCE_WS) as binance_ws:
        try:
            while True:
                msg = await binance_ws.recv()
                await websocket.send_text(msg)
        except Exception:
            await websocket.close()
