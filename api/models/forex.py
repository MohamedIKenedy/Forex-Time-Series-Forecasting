from pydantic import BaseModel
from datetime import datetime as Datetime
from typing import List

class ForexRequest(BaseModel):
    ticker: str
    Data: Datetime
    Open: float
    High: float
    Low: float
    Close: float
    Volume: int


class PredictionRequest(BaseModel):
    ticker: str
    data: List[List[float]]


class PredictionResponse(BaseModel):
    ticker: str
    predictions: List[float]
    confidence: float = 0.0  