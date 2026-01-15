
from fastapi import APIRouter, HTTPException
from services.features_services import FeatureStore
from services.inference_services import InferenceService
import asyncio
from typing import List, Dict, Any

router = APIRouter()
feature_store = FeatureStore()
inference_service = InferenceService()

async def predict_single_ticker(ticker: str, lookback: int = 200) -> Dict[str, Any]:
    """
    Async function to predict for a single ticker.
    """
    try:
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
        
        return {
            "ticker": ticker,
            "predicted_log_return": round(prediction, 6),
            "direction": direction
        }
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
    return {
        "successful_predictions": successful,
        "errors": errors
    }

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

