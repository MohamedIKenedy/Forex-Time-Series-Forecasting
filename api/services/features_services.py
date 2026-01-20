
import pandas as pd
import numpy as np
from kafka import KafkaConsumer
import json
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from dateutil import parser as _dateutil_parser

class FeatureStore:
    """
    Lightweight feature store for FX forecasting.
    Handles data fetching/simulation and feature engineering.
    """
    
    def __init__(self, tickers: list = None, kafka_bootstrap_servers: str = 'localhost:9092', kafka_topic: str = 'fx_data'):
        self.tickers = tickers or [
            "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "USDCAD=X",
            "AUDUSD=X", "NZDUSD=X", "EURMAD=X", "EURRUB=X", "RUBUSD=X"
        ]
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.kafka_topic = kafka_topic
    
    def fetch_realtime_data_from_kafka(self, ticker: str, max_messages: int = 500, timeout_ms: int = 10000) -> pd.DataFrame:
        """
        Fetch real-time data for a ticker from Kafka streaming topics.
        Consumes from instant/hourly/daily topics to build recent historical data.
        """
        topic_patterns = [
            f"instant_{ticker.lower().replace('=', '')}",
            f"hourly_{ticker.lower().replace('=', '')}",
            f"daily_{ticker.lower().replace('=', '')}"
        ]
        
        data = []
        for topic in topic_patterns:
            try:
                consumer = KafkaConsumer(
                    topic,
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    group_id=f"feature-store-inference-{ticker.lower().replace('=', '')}",
                    auto_offset_reset='earliest',  
                    enable_auto_commit=False,
                    consumer_timeout_ms=timeout_ms,
                    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
                )
                
                msg_count = 0
                for message in consumer:
                    record = message.value
                    if record.get('ticker') == ticker:
                        date_field = record.get('timestamp') or record.get('date')
                        if date_field:
                            data.append({
                                'Date': date_field,
                                'Open': float(record.get('open', record.get('Open', 0))),
                                'High': float(record.get('high', record.get('High', 0))),
                                'Low': float(record.get('low', record.get('Low', 0))),
                                'Close': float(record.get('close', record.get('Close', 0))),
                                'Volume': int(record.get('volume', record.get('Volume', 0)))
                            })
                            msg_count += 1
                            if msg_count >= max_messages:
                                break
                
                consumer.close()

                if not data:
                    try:
                        consumer = KafkaConsumer(
                            topic,
                            bootstrap_servers=self.kafka_bootstrap_servers,
                            group_id=f"feature-store-inference-{ticker.lower().replace('=', '')}",
                            auto_offset_reset='latest',
                            enable_auto_commit=False,
                            consumer_timeout_ms=max(3000, timeout_ms // 2),
                            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
                        )

                        msg_count = 0
                        for message in consumer:
                            record = message.value
                            if record.get('ticker') == ticker:
                                date_field = record.get('timestamp') or record.get('date')
                                if date_field:
                                    data.append({
                                        'Date': date_field,
                                        'Open': float(record.get('open', record.get('Open', 0))),
                                        'High': float(record.get('high', record.get('High', 0))),
                                        'Low': float(record.get('low', record.get('Low', 0))),
                                        'Close': float(record.get('close', record.get('Close', 0))),
                                        'Volume': int(record.get('volume', record.get('Volume', 0)))
                                    })
                                    msg_count += 1
                                    if msg_count >= min(50, max_messages):
                                        break

                        consumer.close()
                    except Exception as e:
                        print(f"Failed to consume (latest) from {topic}: {e}")

                if data:
                    break 
                    
            except Exception as e:
                print(f"Failed to consume from {topic}: {e}")
                continue
        
        if not data:
            raise ValueError(f"No real-time data found for {ticker} in any Kafka streaming topic")
        
        df = pd.DataFrame(data)
        
        date_series = df['Date'].astype(str).str.replace(r'Z$', '+00:00', regex=True)

        parsed = pd.to_datetime(date_series, utc=True, errors='coerce')
        if parsed.isna().any():
            def _parse_fallback(s):
                try:
                    return _dateutil_parser.parse(s)
                except Exception:
                    return pd.NaT

            parsed = date_series.apply(_parse_fallback)
            parsed = pd.to_datetime(parsed, utc=True, errors='coerce')

        df['Date'] = parsed
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        
        df = df[~df.index.duplicated(keep='last')]
        
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        
        df['Close_log'] = np.log(df['Close'])
        df['Close_log_return'] = df['Close_log'].diff()
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        df.fillna(0, inplace=True) 
        
        return df
    
    def create_lagged_features_for_inference(self, df_history: pd.DataFrame, lookback: int = 200) -> pd.DataFrame:
        """
        Create lagged features for inference from historical data.
        Feature store method: Computes features on demand.
        """
        features = df_history.copy()

        for col in ['Open', 'High', 'Low', 'Close']:
            if col in features.columns:
                log_col = f"{col}_log"
                ret_col = f"{col}_log_return"
                features[log_col] = np.log(features[col])
                features[ret_col] = features[log_col].diff()
                features[ret_col] = features[ret_col].fillna(0.0)

        if 'Close_log_return' not in features.columns and 'Close' in features.columns:
            features['Close_log'] = np.log(features['Close'])
            features['Close_log_return'] = features['Close_log'].diff().fillna(0.0)

        for lag in [1, 2, 3, 5, 10, 20, 60, 120, 200]:
            if lag <= lookback and 'Close_log_return' in features.columns:
                features[f'close_log_return_lag_{lag}'] = features['Close_log_return'].shift(lag)

        for window in [5, 10, 20, 60]:
            if window <= lookback and 'Close_log_return' in features.columns:
                shifted = features['Close_log_return'].shift(1)
                features[f'close_log_return_mean_{window}'] = shifted.rolling(window).mean()
                features[f'close_log_return_std_{window}'] = shifted.rolling(window).std()

        features.replace([np.inf, -np.inf], np.nan, inplace=True)
        features.ffill(inplace=True)
        features.bfill(inplace=True)
        features = features.fillna(0.0)

        return features

    def _load_metadata(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Read the metadata JSON for the provided ticker."""
        try:
            base_dir = Path(__file__).resolve().parent.parent
            meta_path = base_dir / 'inference_models' / ticker / 'metadata.json'
            if not meta_path.exists():
                return None
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def _metadata_features(self, ticker: str) -> Optional[List[str]]:
        metadata = self._load_metadata(ticker)
        if not metadata:
            return None
        feats = metadata.get('features')
        if isinstance(feats, list) and feats:
            return feats
        return None

    def get_metadata(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self._load_metadata(ticker)
    
    def get_inference_features(self, ticker: str, lookback: int = 200) -> Optional[pd.DataFrame]:
        """
        Feature store interface: Get features for inference from real-time Kafka stream.
        Fetches real-time data from Kafka, computes features, and returns the latest feature set.
        """
        try:
            df_history = self.fetch_realtime_data_from_kafka(ticker, max_messages=lookback + 250)
            
            if df_history.empty:
                print(f"No data available from Kafka stream for {ticker}")
                return None
            
            df_filtered = df_history.tail(lookback + 250).copy()
            
            features_full = self.create_lagged_features_for_inference(df_filtered, lookback=lookback)

            cols = self._metadata_features(ticker) or []
            if cols:
                for c in cols:
                    if c not in features_full.columns:
                        features_full[c] = 0.0
                features_full = features_full[cols]

            result = features_full.tail(1)
            
            if result.empty:
                print(f"No valid features after processing for {ticker}")
                return None
            
            result = result.apply(pd.to_numeric, errors='coerce').fillna(0.0)
            return result
            
        except Exception as e:
            print(f"Error generating features for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return None