from fastapi import APIRouter, HTTPException
from services.features_services import FeatureStore
from services.inference_services import InferenceService
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta

router = APIRouter()
feature_store = FeatureStore()
inference_service = InferenceService()

inference_cache: Dict[str, Dict[str, Any]] = {}


def get_cached_inference(ticker: str) -> Dict[str, Any] | None:
    """Get cached inference if it exists and is from today (UTC)"""
    if ticker not in inference_cache:
        return None

    cached = inference_cache[ticker]
    today = datetime.utcnow().date().isoformat()

    if cached.get("date") == today:
        return cached["result"]

    del inference_cache[ticker]
    return None


def set_cached_inference(ticker: str, result: Dict[str, Any]) -> None:
    """Cache inference result with today's date"""
    today = datetime.utcnow().date().isoformat()
    inference_cache[ticker] = {
        "result": result,
        "timestamp": datetime.utcnow(),
        "date": today,
    }


async def predict_single_ticker(ticker: str, lookback: int = 200) -> Dict[str, Any]:
    """
    Async function to predict for a single ticker.
    Uses daily cache to avoid repeated inference computations.
    """
    try:
        # Check cache first
        cached = get_cached_inference(ticker)
        if cached is not None:
            return cached

        if ticker not in feature_store.tickers:
            return {"ticker": ticker, "error": "Unsupported ticker"}

        features_df = feature_store.get_inference_features(ticker, lookback=lookback)
        if features_df is None or features_df.empty:
            return {"ticker": ticker, "error": "Features not available"}

        prediction = inference_service.predict(ticker, features_df.values)
        if prediction is None:
            return {"ticker": ticker, "error": "Inference failed"}

        if prediction > 0.0001:
            direction = "UP"
        elif prediction < -0.0001:
            direction = "DOWN"
        else:
            direction = "SIDEWAYS"

        result = {
            "ticker": ticker,
            "predicted_log_return": round(prediction, 6),
            "direction": direction,
        }

        # Cache the result
        set_cached_inference(ticker, result)

        return result
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


@router.post("/inference")
async def run_batch_inference(tickers: List[str], lookback: int = 200):
    """
    Inference endpoint for batch FX forecasting.
    Runs predictions for multiple tickers in parallel.
    """
    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")

    tasks = [predict_single_ticker(ticker, lookback) for ticker in tickers]
    results = await asyncio.gather(*tasks)

    successful = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]
    return {"successful_predictions": successful, "errors": errors}


@router.get("/inference/{ticker}/metadata")
async def get_inference_metadata(ticker: str):
    metadata = feature_store.get_metadata(ticker)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Metadata not found for {ticker}")
    return metadata


@router.get("/inference/{ticker}")
async def run_single_inference(ticker: str, lookback: int = 200):
    """
    Inference endpoint for single FX forecasting.
    """
    result = await predict_single_ticker(ticker, lookback)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result
