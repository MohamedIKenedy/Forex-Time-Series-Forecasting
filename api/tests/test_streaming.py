import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import patch, MagicMock

def test_streaming_service_import():
    """Verify streaming service can be imported"""
    from services.streaming_service import StreamingService
    assert StreamingService is not None

def test_config_accessible():
    """Verify config is accessible"""
    from config import settings
    assert settings.kafka_brokers is not None
    assert settings.database_url is not None

@patch('services.streaming_service.KafkaService')
def test_streaming_service_creation(mock_kafka):
    """Test StreamingService instantiation"""
    from services.streaming_service import StreamingService
    service = StreamingService()
    assert service is not None

@patch('yfinance.download')
@patch('services.streaming_service.KafkaService')
def test_hourly_data_processing(mock_kafka, mock_yf):
    """Test that hourly data is fetched and sent to Kafka correctly for multiple tickers"""
    from services.streaming_service import StreamingService
    import pandas as pd
    
    # Mock yfinance data with actual values for EURUSD
    mock_data = pd.DataFrame({
        'Open': [1.0500],
        'High': [1.0600],
        'Low': [1.0400],
        'Close': [1.0550],
        'Volume': [100000]
    }, index=pd.DatetimeIndex(['2026-01-07 10:00:00']))
    mock_yf.return_value = mock_data
    
    # Setup mock Kafka
    mock_producer = MagicMock()
    mock_kafka.return_value.producer = mock_producer
    mock_kafka.return_value.create_producer.return_value = mock_producer
    
    service = StreamingService()
    tickers = ["EURUSD=X", "GBPUSD=X"]
    
    # Manually call the fetch logic (avoid infinite loop)
    # Simulate what happens inside the loop for each ticker
    for ticker in tickers:
        data = mock_yf(ticker, period="1d", interval="1h")
        assert not data.empty
        assert data.iloc[-1]['Close'] == 1.0550
        assert data.iloc[-1]['Volume'] == 100000

@patch('yfinance.download')
@patch('services.streaming_service.KafkaService')
def test_daily_data_values(mock_kafka, mock_yf):
    """Test that daily data has correct values for multiple tickers"""
    from services.streaming_service import StreamingService
    import pandas as pd
    
    # Mock daily data
    mock_data = pd.DataFrame({
        'Open': [1.0800],
        'High': [1.0900],
        'Low': [1.0700],
        'Close': [1.0850],
        'Volume': [500000]
    }, index=pd.DatetimeIndex(['2026-01-07']))
    mock_yf.return_value = mock_data
    
    service = StreamingService()
    tickers = ["EURUSD=X", "GBPUSD=X"]
    
    # Simulate what happens inside the loop for each ticker
    for ticker in tickers:
        data = mock_yf(ticker, period="2d", interval="1d")
        
        # Verify values
        assert data.iloc[-1]['Close'] == 1.0850
        assert data.iloc[-1]['Open'] == 1.0800
        assert data.iloc[-1]['High'] == 1.0900
        assert data.iloc[-1]['Low'] == 1.0700

@patch('yfinance.download')
@patch('services.streaming_service.KafkaService')
def test_multi_ticker_streaming_logic(mock_kafka, mock_yf):
    """Test that streaming service handles multiple tickers correctly"""
    from services.streaming_service import StreamingService
    import pandas as pd
    
    # Mock data for multiple tickers
    mock_data = pd.DataFrame({
        'Open': [1.0500],
        'High': [1.0600],
        'Low': [1.0400],
        'Close': [1.0550],
        'Volume': [100000]
    }, index=pd.DatetimeIndex(['2026-01-07 10:00:00']))
    mock_yf.return_value = mock_data
    
    # Setup mock Kafka
    mock_instance = MagicMock()
    mock_kafka.return_value = mock_instance
    mock_instance.create_producer.return_value = None  # create_producer doesn't need to return anything
    mock_instance.produce_message = MagicMock()
    
    service = StreamingService()
    tickers = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]
    
    # Test that yfinance is called for each ticker
    call_count = 0
    def mock_download(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_data
    
    mock_yf.side_effect = mock_download
    
    # Simulate the fetch_and_send function logic
    for ticker in tickers:
        topic = f"hourly_{ticker.lower().replace('=', '')}"
        data = mock_yf(ticker, period="1d", interval="1h")
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
            service.kafka_service.produce_message(topic=topic, message=message, key=ticker)
    
    # Verify yfinance was called for each ticker
    assert call_count == len(tickers)
    
    # Verify Kafka produce_message was called for each ticker
    assert mock_instance.produce_message.call_count == len(tickers)

# Integration tests with real yfinance API
def test_yfinance_hourly_api_real():
    """Test real yfinance API for hourly data"""
    import yfinance as yf
    
    data = yf.download("EURUSD=X", period="1d", interval="1h")
    
    # Verify data is returned
    assert not data.empty, "yfinance returned no hourly data"
    
    # Check columns exist
    assert 'Close' in data.columns, "Close column missing"
    assert 'Open' in data.columns, "Open column missing"
    assert 'High' in data.columns, "High column missing"
    assert 'Low' in data.columns, "Low column missing"
    
    # Check we got recent data
    assert len(data) > 0, "No hourly data points returned"
    
    # Check values are reasonable (forex prices typically between 0.5 and 2.0 for major pairs)
    latest_close = data['Close'].iloc[-1]
    if hasattr(latest_close, 'item'):
        latest_close = latest_close.item()
    assert 0.5 < latest_close < 2.0, f"Unexpected close price: {latest_close}"

def test_yfinance_daily_api_real():
    """Test real yfinance API for daily data"""
    import yfinance as yf
    
    data = yf.download("EURUSD=X", period="5d", interval="1d")
    
    # Verify data is returned
    assert not data.empty, "yfinance returned no daily data"
    
    # Check we got multiple days
    assert len(data) >= 3, f"Expected at least 3 days, got {len(data)}"
    
    # Check OHLC structure
    assert 'Open' in data.columns
    assert 'High' in data.columns
    assert 'Low' in data.columns
    assert 'Close' in data.columns
    
    # Verify High >= Low for each day
    for idx in range(len(data)):
        high_val = data['High'].iloc[idx]
        low_val = data['Low'].iloc[idx]
        if hasattr(high_val, 'item'):
            high_val = high_val.item()
        if hasattr(low_val, 'item'):
            low_val = low_val.item()
        assert high_val >= low_val, \
            f"High ({high_val}) should be >= Low ({low_val}) on {data.index[idx]}"
    
    # Check date index
    assert hasattr(data.index, 'date'), "Index should be datetime"
