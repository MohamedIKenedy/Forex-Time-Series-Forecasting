import pytest
import pandas as pd
from fastapi import HTTPException
from unittest.mock import patch, MagicMock
from api.routes.stream import fetch_yfinance_data, get_forex_data

# --- Fixtures ---


@pytest.fixture
def mock_yfinance_ticker():
    with patch("api.routes.stream.yf.Ticker") as mock_ticker:
        yield mock_ticker


@pytest.fixture
def mock_streaming_service():
    with patch("api.routes.stream.streaming_service_instance", None):
        yield


# --- Tests for fetch_yfinance_data ---


def test_fetch_yfinance_data_success(mock_yfinance_ticker):
    """Test successful data fetching."""
    mock_ticker_instance = MagicMock()
    mock_df = pd.DataFrame(
        {
            "Open": [1.05],
            "High": [1.06],
            "Low": [1.04],
            "Close": [1.055],
            "Volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    mock_ticker_instance.history.return_value = mock_df
    mock_yfinance_ticker.return_value = mock_ticker_instance

    result = fetch_yfinance_data("EURUSD=X", "1d", "5m")
    assert result is not None
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1


def test_fetch_yfinance_data_empty_response(mock_yfinance_ticker):
    """Test when yfinance returns empty DataFrame."""
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = pd.DataFrame()  # Empty
    mock_yfinance_ticker.return_value = mock_ticker_instance

    result = fetch_yfinance_data("EURUSD=X", "1d", "5m")
    assert result is None


def test_fetch_yfinance_data_exception(mock_yfinance_ticker):
    """Test when yfinance raises an exception."""
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.side_effect = Exception("Network error")
    mock_yfinance_ticker.return_value = mock_ticker_instance

    result = fetch_yfinance_data("EURUSD=X", "1d", "5m")
    assert result is None


# --- Tests for get_forex_data ---


@pytest.mark.asyncio
async def test_get_forex_data_primary_strategy_success(mock_yfinance_ticker):
    """Test successful data retrieval using the first config (1d/5m)."""
    mock_ticker_instance = MagicMock()
    mock_df = pd.DataFrame(
        {
            "Open": [1.05],
            "High": [1.06],
            "Low": [1.04],
            "Close": [1.055],
            "Volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    mock_ticker_instance.history.return_value = mock_df
    mock_yfinance_ticker.return_value = mock_ticker_instance

    result = await get_forex_data("EURUSD=X", period="1d")

    assert result["ticker"] == "EURUSD=X"
    assert result["period"] == "1d"
    assert result["interval"] == "5m"
    assert len(result["data"]) == 1
    assert result["data"][0]["Close"] == 1.055
    assert result["latest_price"] == 1.055
    assert result["streaming"] is False


@pytest.mark.asyncio
async def test_get_forex_data_fallback_strategy(mock_yfinance_ticker):
    """Test fallback to second config (5d/1h) when first fails."""
    mock_ticker_instance = MagicMock()
    # First call returns None (empty), second returns data
    mock_ticker_instance.history.side_effect = [
        pd.DataFrame(),
        pd.DataFrame(
            {
                "Open": [1.05],
                "High": [1.06],
                "Low": [1.04],
                "Close": [1.055],
                "Volume": [1000],
            },
            index=pd.to_datetime(["2023-01-01"]),
        ),
    ]
    mock_yfinance_ticker.return_value = mock_ticker_instance

    result = await get_forex_data("EURUSD=X", period="1d")

    assert result["period"] == "1d"
    assert result["interval"] == "5m"
    assert len(result["data"]) == 1


@pytest.mark.asyncio
async def test_get_forex_data_all_fail(mock_yfinance_ticker):
    """Test when all configs fail to return data."""
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = pd.DataFrame()  # Always empty
    mock_yfinance_ticker.return_value = mock_ticker_instance

    with pytest.raises(HTTPException) as exc_info:
        await get_forex_data("INVALID_TICKER")

    assert exc_info.value.status_code == 404
    assert "No data available" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_forex_data_streaming_integration(mock_yfinance_ticker, monkeypatch):
    """Test integration with streaming cache."""
    from api.routes import stream

    # Mock active streaming
    mock_streaming = MagicMock()
    mock_streaming.is_running = True
    monkeypatch.setattr(stream, "streaming_service_instance", mock_streaming)
    monkeypatch.setattr(
        stream,
        "latest_data_cache",
        {"EURUSD=X": {"1d_5m": {"close": 1.1000, "other": "data"}}},
    )

    mock_ticker_instance = MagicMock()
    mock_df = pd.DataFrame(
        {
            "Open": [1.05],
            "High": [1.06],
            "Low": [1.04],
            "Close": [1.055],
            "Volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    mock_ticker_instance.history.return_value = mock_df
    mock_yfinance_ticker.return_value = mock_ticker_instance

    result = await get_forex_data("EURUSD=X")

    assert result["streaming"] is True
    assert "latest" in result
    assert result["latest"]["close"] == 1.1000
    assert result["latest_price"] == 1.1000  # Prefers cache
