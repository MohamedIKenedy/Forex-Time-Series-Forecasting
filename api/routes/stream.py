from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import yfinance as yf
from services.streaming_service import StreamingService
from services.utils.stream_utils import (
    update_cache_and_broadcast,
    update_cache_only,
    _topic_name,
    _ws_mode,
    _start_kafka_bridge,
    _stop_kafka_bridge,
    fetch_yfinance_data,
    latest_data_cache,
    manager,
    set_ws_broadcast_loop,
)
import threading
import asyncio
import pandas as pd
import os

router = APIRouter()

streaming_service_instance: StreamingService = None
streaming_thread = None

tickers = [
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "USDCHF=X",
    "USDCAD=X",
    "AUDUSD=X",
    "NZDUSD=X",
    "EURMAD=X",
    "EURRUB=X",
    "RUBUSD=X",
]


@router.post("/start_streaming")
async def start_streaming():
    global streaming_service_instance, streaming_thread

    mode = _ws_mode()
    topics = [_topic_name("hourly", t) for t in tickers]
    use_kafka = mode in {"auto", "kafka"}
    kafka_ok = False
    if use_kafka:
        try:
            _start_kafka_bridge(topics)
            kafka_ok = True
        except Exception as e:
            if mode == "kafka":
                raise HTTPException(
                    status_code=503, detail=f"Failed to start Kafka bridge: {e}"
                )
            print(
                f"[WS_UPDATES_MODE=auto] Kafka bridge unavailable, falling back to direct WS: {e}"
            )

    if streaming_service_instance and streaming_service_instance.is_running:
        streaming_service_instance.stop()
        if streaming_thread:
            streaming_thread.join(timeout=5)

    streaming_service_instance = StreamingService()
    # When Kafka is OK, only update cache (Kafka bridge will broadcast)
    # Otherwise, update cache and broadcast directly
    callback = update_cache_only if kafka_ok else update_cache_and_broadcast
    streaming_thread = threading.Thread(
        target=lambda: streaming_service_instance.stream_hourly(tickers, callback),
        daemon=True,
    )
    streaming_thread.start()
    return {"message": "Streaming started", "tickers": tickers}


@router.post("/start_instant_streaming")
async def start_instant_streaming():
    global streaming_service_instance, streaming_thread

    mode = _ws_mode()
    topics = [_topic_name("instant", t) for t in tickers]
    use_kafka = mode in {"auto", "kafka"}
    kafka_ok = False
    if use_kafka:
        try:
            _start_kafka_bridge(topics)
            kafka_ok = True
        except Exception as e:
            if mode == "kafka":
                raise HTTPException(
                    status_code=503, detail=f"Failed to start Kafka bridge: {e}"
                )
            print(
                f"[WS_UPDATES_MODE=auto] Kafka bridge unavailable, falling back to direct WS: {e}"
            )

    if streaming_service_instance and streaming_service_instance.is_running:
        streaming_service_instance.stop()
        if streaming_thread:
            streaming_thread.join(timeout=5)

    streaming_service_instance = StreamingService()
    # When Kafka is OK, only update cache (Kafka bridge will broadcast)
    # Otherwise, update cache and broadcast directly
    callback = update_cache_only if kafka_ok else update_cache_and_broadcast
    streaming_thread = threading.Thread(
        target=lambda: streaming_service_instance.stream_instant(tickers, callback),
        daemon=True,
    )
    streaming_thread.start()
    return {"message": "Instant streaming started", "tickers": tickers}


@router.post("/stop_streaming")
async def stop_streaming():

    _stop_kafka_bridge()

    if not streaming_service_instance or not streaming_service_instance.is_running:
        return {"message": "Streaming not active"}

    streaming_service_instance.stop()
    if streaming_thread:
        streaming_thread.join(timeout=5)

    _stop_kafka_bridge()

    return {"message": "Streaming stopped"}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    set_ws_broadcast_loop(asyncio.get_running_loop())
    print(
        f"[WebSocket] Client connected, total connections: {len(manager.active_connections)}"
    )
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(
            f"[WebSocket] Client disconnected, remaining connections: {len(manager.active_connections)}"
        )


@router.get("/status")
async def get_status():
    is_active = streaming_service_instance and streaming_service_instance.is_running
    return {
        "status": "streaming" if is_active else "stopped",
        "mode": (
            getattr(streaming_service_instance, "mode", None) if is_active else None
        ),
        "tickers": tickers if is_active else [],
        "cached_tickers": list(latest_data_cache.keys()),
    }


@router.get("/data/{ticker}")
async def get_forex_data(ticker: str, period: str = "1d", interval: str = None):
    """Fetch historical forex data for a given ticker and period."""

    period_config_map = {
        "1d": ("1d", "5m"),
        "5d": ("5d", "5m"),
        "1mo": ("2mo", "1d"),
        "3mo": ("3mo", "1d"),
        "6mo": ("6mo", "1d"),
        "1y": ("1y", "1d"),
        "2y": ("2y", "1d"),
        "5y": ("5y", "1wk"),
        "max": ("max", "1mo"),
    }

    if period in period_config_map:
        target_period, default_interval = period_config_map[period]
        target_interval = interval if interval else default_interval
    else:
        target_period = period
        target_interval = interval if interval else "1d"

    data = fetch_yfinance_data(ticker, target_period, target_interval)
    used_period = target_period
    used_interval = target_interval

    if data is None:
        fallback_configs = [
            ("1d", "5m"),
            ("5d", "1h"),
            ("1mo", "1d"),
        ]

        for p, i in fallback_configs:
            data = fetch_yfinance_data(ticker, p, i)
            if data is not None:
                used_period = p
                used_interval = i
                print(f"Fallback success: {ticker} with {p}/{i}")
                break

    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No data available for {ticker}. Market may be closed or ticker invalid.",
        )

    historical_data = []
    for idx, row in data.iterrows():
        try:
            record = {
                "Date": idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
            }
            for col in ["Open", "High", "Low", "Close"]:
                if col in data.columns and pd.notna(row[col]):
                    record[col] = float(row[col])
            if "Volume" in data.columns and pd.notna(row["Volume"]):
                record["Volume"] = int(row["Volume"])
            historical_data.append(record)
        except:
            continue

    if not historical_data:
        raise HTTPException(
            status_code=404, detail=f"No valid data points for {ticker}"
        )

    if period == "1mo" and len(historical_data) > 30:
        historical_data = historical_data[-30:]

    latest_price = historical_data[-1].get("Close") if historical_data else None

    is_streaming = streaming_service_instance is not None and streaming_service_instance.is_running

    response = {
        "ticker": ticker,
        "period": period,
        "interval": used_interval,
        "streaming": is_streaming,
        "data": historical_data,
        "latest_price": latest_price,
    }

    if is_streaming and ticker in latest_data_cache:
        partition_key = f"{used_period}_{used_interval}"
        if partition_key in latest_data_cache[ticker]:
            response["latest"] = latest_data_cache[ticker][partition_key]
            response["latest_price"] = latest_data_cache[ticker][partition_key].get(
                "close", latest_price
            )
        else:
            partitions = latest_data_cache[ticker]
            if partitions:
                first_partition = next(iter(partitions.values()))
                response["latest"] = first_partition
                response["latest_price"] = first_partition.get("close", latest_price)

    return response
