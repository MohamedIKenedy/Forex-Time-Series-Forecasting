import config
from services.kafka_service import KafkaService
import os 
import schedule
import time
import yfinance as yf
from config import settings
import psycopg2
from datetime import datetime, timedelta, timezone
from math import isfinite

class StreamingService:
    def __init__(self):
        # Allocate multiple partitions per topic so each ticker lands on a distinct partition via key hashing.
        self.kafka_service = KafkaService(brokers=config.settings.kafka_brokers, topic_partitions=16)
        self.is_running = False
        self.mode = "hourly"
    
    def stream_instant(self, tickers: list, on_message_callback=None):
        """Stream data instantly every second for real-time updates"""
        self.kafka_service.create_producer()
        self.is_running = True
        self.mode = "instant"
        print(f"\n[INSTANT STREAMING] Started for {len(tickers)} tickers")
        print(f"[INSTANT STREAMING] Fetching 1-minute candles every second\n")

        # Remember the last candle we sent per ticker to avoid spamming identical points.
        last_sent: dict[str, tuple[str, float]] = {}

        def get_quote_price(ticker_obj):
            try:
                fi = getattr(ticker_obj, "fast_info", None)
                if not fi:
                    return None
                # fast_info can be dict-like or object; prefer last_price, fallback to regularMarketPrice keys.
                for key in ["last_price", "regularMarketPrice", "lastPrice"]:
                    if hasattr(fi, key):
                        val = getattr(fi, key)
                        if isfinite(val):
                            return float(val)
                    if isinstance(fi, dict) and key in fi:
                        val = fi.get(key)
                        if isfinite(val):
                            return float(val)
            except Exception:
                return None
            return None
        
        def fetch_and_send():
            for ticker in tickers:
                if not self.is_running:
                    break
                topic = f"instant_{ticker.lower().replace('=', '')}"
                try:
                    ticker_obj = yf.Ticker(ticker)

                    # Keep a stable candle resolution for the UI.
                    # For "instant" mode we always target 1-minute candles for the last day.
                    data = None
                    used_period = "1d"
                    used_interval = "1m"
                    try:
                        data = ticker_obj.history(period=used_period, interval=used_interval)
                    except:
                        data = None

                    # Fallback to 2m if 1m is unavailable (some tickers / sessions).
                    if data is None or data.empty:
                        used_interval = "2m"
                        try:
                            data = ticker_obj.history(period=used_period, interval=used_interval)
                        except:
                            data = None
                    
                    latest_close = None

                    if data is not None and not data.empty:
                        latest = data.iloc[-1]
                        latest_close = float(latest["Close"])
                        ts = getattr(latest, "name", None)
                        try:
                            ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                        except Exception:
                            ts_str = str(ts)

                        # Skip sending if candle timestamp and close are unchanged.
                        last_key = last_sent.get(ticker)
                        if last_key and last_key[0] == ts_str and abs(last_key[1] - latest_close) < 1e-12:
                            pass
                        else:
                            message = {
                                "ticker": ticker,
                                "timestamp": ts_str,
                                "period": used_period,
                                "interval": used_interval,
                                "open": float(latest["Open"]),
                                "high": float(latest["High"]),
                                "low": float(latest["Low"]),
                                "close": latest_close,
                                "volume": int(latest["Volume"])
                            }
                            last_sent[ticker] = (ts_str, latest_close)
                            self.kafka_service.produce_message(topic=topic, message=message, key=ticker)
                            if on_message_callback:
                                on_message_callback(ticker, message, period=used_period, interval=used_interval)
                    else:
                        print(f"[WARNING] No data available for {ticker} - market may be closed")

                    # Try to get a fresher quote price to update intraminute.
                    quote_price = get_quote_price(ticker_obj)
                    if quote_price is not None and (latest_close is None or abs(quote_price - latest_close) > 0):
                        now_ts = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                        quote_msg = {
                            "ticker": ticker,
                            "timestamp": now_ts,
                            "period": used_period,
                            "interval": "tick",  # sub-minute quotes; avoid 1m bucket collapse
                            "open": quote_price,
                            "high": quote_price,
                            "low": quote_price,
                            "close": quote_price,
                            "volume": 0,
                        }
                        self.kafka_service.produce_message(topic=topic, message=quote_msg, key=ticker)
                        if on_message_callback:
                            on_message_callback(ticker, quote_msg, period=used_period, interval="tick")
                except Exception as e:
                    print(f"[ERROR] Failed to fetch {ticker}: {e}")
        
        fetch_and_send()
        while self.is_running:
            time.sleep(1)
            fetch_and_send()
    
    def stream_hourly(self, tickers: list, on_message_callback=None):
        """Stream hourly data for multiple tickers"""
        self.kafka_service.create_producer()
        self.is_running = True
        self.mode = "hourly"
        
        def fetch_and_send():
            for ticker in tickers:
                if not self.is_running:
                    break
                topic = f"hourly_{ticker.lower().replace('=', '')}"
                try:
                    ticker_obj = yf.Ticker(ticker)
                    
                    data = None
                    
                    end_date = datetime.now()
                    start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    try:
                        data = ticker_obj.history(start=start_date, end=end_date, interval="1h")
                    except:
                        pass
                    
                    if data is None or data.empty:
                        for period in ["1d", "5d", "1mo"]:
                            try:
                                data = ticker_obj.history(period=period, interval="1h")
                                if data is not None and not data.empty:
                                    break
                            except:
                                continue
                    
                    if data is not None and not data.empty:
                        latest = data.iloc[-1]
                        message = {
                            "ticker": ticker,
                            "timestamp": str(latest.name),
                            "period": "1d",
                            "interval": "1h",
                            "open": float(latest["Open"]),
                            "high": float(latest["High"]),
                            "low": float(latest["Low"]),
                            "close": float(latest["Close"]),
                            "volume": int(latest["Volume"])
                        }
                        self.kafka_service.produce_message(topic=topic, message=message, key=ticker)
                        if on_message_callback:
                            on_message_callback(ticker, message, period="1d", interval="1h")
                    else:
                        print(f"[WARNING] No data available for {ticker} - market may be closed")
                except Exception as e:
                    print(f"[ERROR] Failed to fetch {ticker}: {e}")
        
        fetch_and_send()
        
        schedule.every().hour.do(fetch_and_send)
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def stream_daily(self, tickers: list, on_message_callback=None):
        """Stream daily data for ML model training"""
        self.kafka_service.create_producer()
        self.is_running = True
        self.mode = "daily"
        print(f"\n[DAILY STREAMING] Started for {len(tickers)} tickers")
        
        def fetch_and_send():
            for ticker in tickers:
                if not self.is_running:
                    break
                topic = f"daily_{ticker.lower().replace('=', '')}"
                try:
                    data = yf.download(ticker, period="60d", interval="1d", progress=False, prepost=False)
                    if not data.empty:
                        latest = data.iloc[-1]
                        close_val = float(latest["Close"].iloc[0]) if hasattr(latest["Close"], 'iloc') else float(latest["Close"])
                        message = {
                            "ticker": ticker,
                            "timestamp": str(latest.name),
                            "period": "60d",
                            "interval": "1d",
                            "open": float(latest["Open"].iloc[0]) if hasattr(latest["Open"], 'iloc') else float(latest["Open"]),
                            "high": float(latest["High"].iloc[0]) if hasattr(latest["High"], 'iloc') else float(latest["High"]),
                            "low": float(latest["Low"].iloc[0]) if hasattr(latest["Low"], 'iloc') else float(latest["Low"]),
                            "close": close_val,
                            "volume": int(latest["Volume"].iloc[0]) if hasattr(latest["Volume"], 'iloc') else int(latest["Volume"])
                        }
                        print(f"[{ticker}] ${close_val:.8f} at {str(latest.name)}")
                        self.kafka_service.produce_message(topic=topic, message=message, key=ticker)
                        if on_message_callback:
                            on_message_callback(ticker, message, period="60d", interval="1d")
                except Exception as e:
                    print(f"[ERROR] Failed to fetch {ticker}: {e}")
        
        fetch_and_send()
        schedule.every().day.at("00:00").do(fetch_and_send)
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        """Stop the streaming service"""
        self.is_running = False
    
    def run_daily_streams(self, tickers: list):
        """Run daily streams for multiple tickers"""
        self.kafka_service.create_producer()
        conn = psycopg2.connect(settings.database_url)
        
        def fetch_store_and_send():
            for ticker in tickers:
                topic = f"daily_{ticker.lower().replace('=', '')}"
                data = yf.download(ticker, period="5d", interval="1d")
                if not data.empty:
                    latest = data.iloc[-1]
                    message = {
                        "ticker": ticker,
                        "timestamp": str(latest.name),
                        "open": latest["Open"],
                        "high": latest["High"],
                        "low": latest["Low"],
                        "close": latest["Close"],
                        "volume": int(latest["Volume"])
                    }
                    # Store in DB
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS forex_data_daily (
                                ticker VARCHAR(10),
                                timestamp TIMESTAMP,
                                open FLOAT,
                                high FLOAT,
                                low FLOAT,
                                close FLOAT,
                                volume BIGINT,
                                PRIMARY KEY (ticker, timestamp)
                            )
                        """)
                        cursor.execute(""" 
                            INSERT INTO forex_data_daily (ticker, timestamp, open, high, low, close, volume)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (ticker, timestamp) DO NOTHING
                        """, (ticker, str(latest.name), latest["Open"], latest["High"], latest["Low"], latest["Close"], int(latest["Volume"])))
                        conn.commit()
                    # Produce to Kafka
                    self.kafka_service.produce_message(topic=topic, message=message, key=ticker)
        
        schedule.every().day.at("00:00").do(fetch_store_and_send)
        while True:
            schedule.run_pending()
            time.sleep(1)