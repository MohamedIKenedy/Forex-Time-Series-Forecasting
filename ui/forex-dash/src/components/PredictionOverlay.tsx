import React, { useEffect, useState } from 'react';
import { predictionService, type PredictionResult } from '../services/predictionService';
import './PredictionOverlay.css';

interface PredictionOverlayProps {
  ticker: string;
  onPredictionLoaded?: (prediction: PredictionResult) => void;
}

export const PredictionOverlay: React.FC<PredictionOverlayProps> = ({ ticker, onPredictionLoaded }) => {
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPrediction = async () => {
      setLoading(true);
      setError(null);
      
      const result = await predictionService.getPrediction(ticker);
      
      if (result) {
        setPrediction(result);
        onPredictionLoaded?.(result);
      } else {
        setError('Failed to load prediction');
      }
      
      setLoading(false);
    };

    fetchPrediction();
  }, [ticker, onPredictionLoaded]);

  if (loading) {
    return (
      <div className="prediction-overlay">
        <div className="prediction-content">
          <div className="prediction-loading">Loading prediction...</div>
        </div>
      </div>
    );
  }

  if (error || !prediction) {
    return null;
  }

  const isUptrend = prediction.direction === 'UP';
  const confidence = prediction.confidence || 50;
  const oppositeConfidence = 100 - confidence;

  return (
    <div className="prediction-overlay">
      <div className="prediction-content">
        {/* LONG Analysis */}
        <div className={`prediction-section ${isUptrend ? 'bullish' : 'bearish'}`}>
          <div className="prediction-title">LONG ANALYSIS</div>
          <div className="prediction-percentage">
            {isUptrend ? confidence : oppositeConfidence}%
          </div>
          
          <div className="prediction-details">
            <div className="detail-row">
              <span className="detail-label">LOG RETURN:</span>
              <span className="detail-value">{prediction.predicted_log_return.toFixed(6)}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">DIRECTION:</span>
              <span className={`detail-value ${prediction.direction.toLowerCase()}`}>
                {prediction.direction}
              </span>
            </div>
          </div>

          <div className="confidence-bar">
            <div 
              className={`confidence-fill ${isUptrend ? 'up' : 'down'}`}
              style={{ width: `${isUptrend ? confidence : oppositeConfidence}%` }}
            />
          </div>
        </div>

        {/* SHORT Analysis */}
        <div className={`prediction-section ${!isUptrend ? 'bullish' : 'bearish'}`}>
          <div className="prediction-title">SHORT ANALYSIS</div>
          <div className="prediction-percentage">
            {!isUptrend ? confidence : oppositeConfidence}%
          </div>
          
          <div className="prediction-details">
            <div className="detail-row">
              <span className="detail-label">CONFIDENCE:</span>
              <span className="detail-value">{(confidence).toFixed(0)}%</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">UPDATED:</span>
              <span className="detail-value">Daily</span>
            </div>
          </div>

          <div className="confidence-bar">
            <div 
              className={`confidence-fill ${!isUptrend ? 'up' : 'down'}`}
              style={{ width: `${!isUptrend ? confidence : oppositeConfidence}%` }}
            />
          </div>
        </div>
      </div>

      {/* Refresh button */}
      <button 
        className="prediction-refresh"
        onClick={() => predictionService.clearCache(ticker)}
        title="Refresh prediction"
      >
        ⟳
      </button>
    </div>
  );
};
