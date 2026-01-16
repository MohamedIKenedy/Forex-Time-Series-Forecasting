"""
Forex Model Monitoring Service
Monitors model performance, data drift, and system health
"""

import time
import schedule
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from kafka import KafkaProducer, KafkaConsumer
import logging
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
MODEL_ACCURACY = Gauge('forex_model_accuracy', 'Model prediction accuracy', ['ticker'])
MODEL_LATENCY = Histogram('forex_model_latency_seconds', 'Model prediction latency', ['ticker'])
PREDICTIONS_TOTAL = Counter('forex_predictions_total', 'Total predictions made', ['ticker', 'signal'])
DATA_DRIFT_SCORE = Gauge('forex_data_drift_score', 'Data drift detection score', ['ticker'])

class ForexModelMonitor:
    """Monitor forex model performance and data quality"""

    def __init__(self, api_url: str = "http://localhost:8000", kafka_servers: str = "localhost:9092"):
        self.api_url = api_url
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_servers],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.consumer = KafkaConsumer(
            'forex_predictions',
            bootstrap_servers=[kafka_servers],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )

        # Historical data for drift detection
        self.historical_data = {}
        self.prediction_history = {}

    def check_api_health(self) -> bool:
        """Check if the API is healthy"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_model_metrics(self) -> dict:
        """Get current model performance metrics"""
        try:
            response = requests.get(f"{self.api_url}/metrics")
            return response.json()
        except:
            return {}

    def collect_live_data(self, tickers: list) -> pd.DataFrame:
        """Collect live forex data for drift detection"""
        data = {}
        for ticker in tickers:
            try:
                df = yf.download(ticker, period="1d", interval="1h")
                data[ticker] = df
            except Exception as e:
                logger.error(f"Error collecting data for {ticker}: {e}")

        return pd.DataFrame(data)

    def detect_data_drift(self, current_data: pd.DataFrame, ticker: str) -> float:
        """Detect data drift using statistical methods"""
        if ticker not in self.historical_data:
            self.historical_data[ticker] = current_data[ticker]
            return 0.0

        historical = self.historical_data[ticker]
        current = current_data[ticker]

        # Simple drift detection using distribution comparison
        hist_mean = historical['Close'].mean()
        hist_std = historical['Close'].std()
        curr_mean = current['Close'].mean()
        curr_std = current['Close'].std()

        # Calculate drift score (normalized difference)
        drift_score = abs(curr_mean - hist_mean) / hist_std if hist_std > 0 else 0

        # Update historical data
        self.historical_data[ticker] = pd.concat([historical, current]).tail(100)  # Keep last 100 points

        return drift_score

    def monitor_predictions(self):
        """Monitor prediction performance in real-time"""
        for message in self.consumer:
            prediction = message.value

            ticker = prediction['ticker']
            actual_return = prediction.get('actual_return', 0)
            predicted_signal = prediction['signal']
            probability = prediction['probability']

            # Determine if prediction was correct
            actual_direction = 1 if actual_return > 0.0002 else 0  # Account for transaction costs
            correct = 1 if predicted_signal == actual_direction else 0

            # Update metrics
            MODEL_ACCURACY.labels(ticker=ticker).set(correct)
            PREDICTIONS_TOTAL.labels(ticker=ticker, signal=str(predicted_signal)).inc()

            # Store for analysis
            if ticker not in self.prediction_history:
                self.prediction_history[ticker] = []

            self.prediction_history[ticker].append({
                'timestamp': datetime.now(),
                'predicted': predicted_signal,
                'actual': actual_direction,
                'probability': probability,
                'return': actual_return,
                'correct': correct
            })

            # Keep only recent history
            self.prediction_history[ticker] = self.prediction_history[ticker][-1000:]

    def log_system_status(self):
        """Log overall system status"""
        health = self.check_api_health()
        metrics = self.get_model_metrics()

        status = {
            'timestamp': datetime.now().isoformat(),
            'api_healthy': health,
            'metrics': metrics,
            'data_drift_scores': {}
        }

        # Check data drift for major pairs
        tickers = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
        live_data = self.collect_live_data(tickers)

        for ticker in tickers:
            if ticker in live_data.columns.get_level(0, []):
                drift_score = self.detect_data_drift(live_data, ticker)
                status['data_drift_scores'][ticker] = drift_score
                DATA_DRIFT_SCORE.labels(ticker=ticker).set(drift_score)

        # Send to Kafka for logging
        self.producer.send('system_monitoring', status)

        logger.info(f"System status: API healthy={health}, Data drift scores={status['data_drift_scores']}")

    def generate_report(self):
        """Generate daily performance report"""
        report = {
            'date': datetime.now().date().isoformat(),
            'model_performance': {},
            'data_quality': {},
            'system_health': self.check_api_health()
        }

        # Analyze prediction performance
        for ticker, history in self.prediction_history.items():
            if history:
                df = pd.DataFrame(history)
                accuracy = df['correct'].mean()
                avg_return = df[df['predicted'] == 1]['return'].mean()
                total_predictions = len(df)

                report['model_performance'][ticker] = {
                    'accuracy': accuracy,
                    'avg_return': avg_return,
                    'total_predictions': total_predictions
                }

        # Log report
        self.producer.send('daily_reports', report)
        logger.info(f"Daily report generated: {report}")

def main():
    """Main monitoring loop"""
    logger.info("Starting Forex Model Monitoring Service...")

    # Start Prometheus metrics server
    start_http_server(9090)
    logger.info("Prometheus metrics server started on port 9090")

    monitor = ForexModelMonitor()

    # Schedule monitoring tasks
    schedule.every(1).minutes.do(monitor.log_system_status)
    schedule.every(1).hours.do(monitor.generate_report)

    # Start prediction monitoring in background
    import threading
    prediction_thread = threading.Thread(target=monitor.monitor_predictions, daemon=True)
    prediction_thread.start()

    # Main loop
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()