from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
from typing import List, Dict, Any

router = APIRouter()


def get_available_tickers_metadata() -> List[Dict[str, Any]]:
    """
    Get metadata for all available tickers.
    """
    base_dir = Path(__file__).resolve().parent.parent
    inference_dir = base_dir / "inference_models"

    tickers_metadata = []

    if not inference_dir.exists():
        return tickers_metadata

    for ticker_dir in inference_dir.iterdir():
        if ticker_dir.is_dir():
            metadata_file = ticker_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)

                    # Extract relevant info for the UI
                    ticker_info = {
                        "symbol": metadata["ticker"],
                        "name": get_ticker_display_name(metadata["ticker"]),
                        "status": "active",  # All models are active if metadata exists
                        "accuracy": round(metadata["metrics"]["dir_acc"] * 100, 1),
                        "performance_status": metadata["performance_status"],
                        "mae": round(metadata["metrics"]["mae"], 6),
                        "rmse": round(metadata["metrics"]["rmse"], 6),
                        "sharpe": round(metadata["metrics"]["sharpe"], 2),
                        "max_dd": round(metadata["metrics"]["max_dd"], 4),
                        "ic": round(metadata["metrics"]["ic"], 3),
                        "hit_rate": round(metadata["metrics"]["hit_rate"], 3),
                    }
                    tickers_metadata.append(ticker_info)
                except Exception as e:
                    print(f"Error loading metadata for {ticker_dir.name}: {e}")

    return tickers_metadata


def get_ticker_display_name(ticker: str) -> str:
    """
    Convert ticker symbol to display name.
    """
    ticker_map = {
        "EURUSD=X": "Euro / US Dollar",
        "GBPUSD=X": "British Pound / US Dollar",
        "USDJPY=X": "US Dollar / Japanese Yen",
        "AUDUSD=X": "Australian Dollar / US Dollar",
        "USDCAD=X": "US Dollar / Canadian Dollar",
        "USDCHF=X": "US Dollar / Swiss Franc",
        "NZDUSD=X": "New Zealand Dollar / US Dollar",
        "EURMAD=X": "Euro / Moroccan Dirham",
        "EURRUB=X": "Euro / Russian Ruble",
        "RUBUSD=X": "Russian Ruble / US Dollar",
    }
    return ticker_map.get(ticker, ticker)


@router.get("/tickers")
async def get_tickers():
    """
    Get list of available tickers with their metadata.
    """
    try:
        tickers = get_available_tickers_metadata()
        return {"tickers": tickers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tickers: {str(e)}")
