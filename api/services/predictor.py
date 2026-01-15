from exported_models import *
import torch
import torch.nn as nn
import onnxruntime as ort
from sklearn.preprocessing import StandardScaler
import joblib



class Predictor():
    def __init__(self, ticker: str, model_path: str, ort_session=None, scaler_path: str = None, window_size: int = 30, forecast_horizon: int = 3):
        self.ticker = ticker
        self.model_path = model_path
        self.ort_session = ort_session
        self.scaler_path = scaler_path

    def preprocess(self, data):
        """ Preprocess input data to match model requirements used in training """
        if self.scaler_path:
            if not hasattr(self, 'scaler'):
                self.scaler = joblib.load(self.scaler_path)
        scaled_data = self.scaler.transform(data)
        return scaled_data

    
    def predict(self, data):
        # Preprocess data
        preprocessed_data = self.preprocess(data)
        input_tensor = torch.tensor(preprocessed_data, dtype=torch.float32).unsqueeze(0)

        # ONNX Runtime inference
        ort_inputs = {self.ort_session.get_inputs()[0].name: input_tensor.numpy()}
        ort_outs = self.ort_session.run(None, ort_inputs)

        return ort_outs[0]
    
    