from typing import Any, Dict
import asyncio
import os
import pandas as pd
import yfinance as yf
from services.conn_management import ConnectionManager
from services.kafka_bridge import KafkaWebSocketBridge

# Shared state
manager = ConnectionManager()
kafka_bridge: KafkaWebSocketBridge | None = None
ws_broadcast_loop: asyncio.AbstractEventLoop | None = None
latest_data_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}


def set_ws_broadcast_loop(loop: asyncio.AbstractEventLoop):
    """Set the WebSocket broadcast event loop"""
    global ws_broadcast_loop
    ws_broadcast_loop = loop
    print(f"[WebSocket] Event loop set: {ws_broadcast_loop is not None}")


def update_cache_and_broadcast(ticker: str, message: Dict[str, Any], period: str = "1d", interval: str = "5m"):
    """Update cache with partitioned data and broadcast to WebSocket clients"""
    
    partition_key = f"{period}_{interval}"
    
    if ticker not in latest_data_cache:
        latest_data_cache[ticker] = {}
    
    latest_data_cache[ticker][partition_key] = message
    
    payload = {
        "type": "price_update",
        "ticker": ticker,
        "data": message,
        "partition": partition_key,
    }

    if ws_broadcast_loop is None:
        print(f"[WebSocket] No broadcast loop available for {ticker}")
        return
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(payload), ws_broadcast_loop)
    except Exception as e:
        print(f"Broadcast error for {ticker}: {e}")


def update_cache_only(ticker: str, message: Dict[str, Any], period: str = "1d", interval: str = "5m"):
    """Update the cache without broadcasting.

    When Kafka server-side mode is enabled, the WS broadcast should come from Kafka consumption.
    """
    partition_key = f"{period}_{interval}"
    if ticker not in latest_data_cache:
        latest_data_cache[ticker] = {}
    latest_data_cache[ticker][partition_key] = message


def _topic_name(prefix: str, ticker: str) -> str:
    return f"{prefix}_{ticker.lower().replace('=', '')}"


def _start_kafka_bridge(topics: list[str]):
    global kafka_bridge
    if kafka_bridge and kafka_bridge.is_running:
        return

    def handle_kafka_message(msg: Dict[str, Any]):
        try:
            t = msg.get("ticker")
            if not t:
                return
            period = msg.get("period") or "1d"
            interval = msg.get("interval") or "1m"
            # Keep cache in sync and broadcast to WS.
            update_cache_and_broadcast(t, msg, period=period, interval=interval)
        except Exception as e:
            print(f"[Kafka Handler] Error processing message: {e}")
            return

    kafka_bridge = KafkaWebSocketBridge(on_message=handle_kafka_message)
    kafka_bridge.start(topics)


def _ws_mode() -> str:
    return (os.environ.get("WS_UPDATES_MODE") or "kafka").strip().lower()


def _stop_kafka_bridge():
    global kafka_bridge
    if kafka_bridge:
        try:
            kafka_bridge.stop()
        except Exception:
            pass
    kafka_bridge = None


def fetch_yfinance_data(ticker: str, period: str, interval: str):
    """Safe wrapper for yfinance data fetching"""
    try:
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period=period, interval=interval)
        
        if hist is not None and isinstance(hist, pd.DataFrame) and not hist.empty:
            return hist
        return None
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        return None
