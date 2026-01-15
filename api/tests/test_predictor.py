import sys
import os
import pytest
import onnxruntime as ort
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.predictor import Predictor

def test_predictor_predict():
    # Use actual ONNX model and scaler
    model_path = 'exported_models/EURUSD=X/model_fold_3.onnx'
    scaler_path = 'exported_models/scalers/EURUSD=X/best_scaler_x.pkl'
    ort_session = ort.InferenceSession(model_path)
    
    predictor = Predictor(ticker='EURUSD', model_path=model_path, ort_session=ort_session, scaler_path=scaler_path)
    

    num_features = 15
    window_size = 30
    mock_data = [[0.1] * num_features for _ in range(window_size)] 
    
    result = predictor.predict(mock_data)
    
    # Assert result is returned (numpy array from ONNX)
    assert isinstance(result, (list, tuple, np.ndarray))