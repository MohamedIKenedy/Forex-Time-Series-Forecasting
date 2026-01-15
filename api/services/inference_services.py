
import os
import json
import joblib
import onnxruntime as ort
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any

class InferenceService:
    """
    Service for loading models and running inference.
    """
    
    def __init__(self):
        self.model_cache: Dict[str, Any] = {}  # Cache loaded models/scalers
    
    def load_model_artifacts(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Load model, scaler, and metadata for a ticker.
        """
        base_dir = Path(__file__).resolve().parent.parent
        inference_dir = base_dir / "inference_models" / ticker
        if not inference_dir.exists():
            raise ValueError(f"Model artifacts directory missing for {ticker}: {inference_dir}")
        
        if ticker not in self.model_cache:
            try:
                with open(inference_dir / "metadata.json", 'r') as f:
                    metadata = json.load(f)
                scaler = joblib.load(inference_dir / "scaler.pkl")
                ort_session = ort.InferenceSession(str(inference_dir / "model.onnx"))
                self.model_cache[ticker] = {
                    'metadata': metadata,
                    'scaler': scaler,
                    'ort_session': ort_session,
                    'feature_columns': metadata['features']
                }
            except Exception as e:
                raise ValueError(f"Error loading artifacts for {ticker}: {e}")
        return self.model_cache[ticker]
    
    def predict(self, ticker: str, features: np.ndarray) -> Optional[float]:
        """
        Run inference on scaled features.
        """
        artifacts = self.load_model_artifacts(ticker)
        
        try:
            ort_session = artifacts['ort_session']
            scaler = artifacts['scaler']
            features_scaled = scaler.transform(features)
            ort_inputs = {ort_session.get_inputs()[0].name: features_scaled.astype(np.float32)}
            ort_outs = ort_session.run(None, ort_inputs)
            return ort_outs[0][0].item()
        except Exception as e:
            raise ValueError(f"Error during prediction for {ticker}: {e}")