/**
 * Prediction Service - Fetches and caches model predictions for chart display
 */

interface PredictionResult {
  ticker: string;
  predicted_log_return: number;
  direction: 'UP' | 'DOWN' | 'SIDEWAYS';
  timestamp?: string;
  confidence?: number; // 0-100
}

interface CachedPrediction extends PredictionResult {
  fetchedAt: number;
}

const CACHE_DURATION_MS = 24 * 60 * 60 * 1000;
const API_BASE_URL = (window as any).env?.REACT_APP_API_URL || 'http://localhost:8000';

class PredictionService {
  private cache: Map<string, CachedPrediction> = new Map();

  /**
   * Fetch prediction for a single ticker
   */
  async getPrediction(ticker: string, useCache = true): Promise<PredictionResult | null> {
    // Check cache
    if (useCache) {
      const cached = this.cache.get(ticker);
      if (cached && Date.now() - cached.fetchedAt < CACHE_DURATION_MS) {
        return cached;
      }
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/inference/${ticker}`);
      if (!response.ok) {
        console.error(`Failed to fetch prediction for ${ticker}`);
        return null;
      }

      const data = await response.json();
      const prediction: PredictionResult = {
        ticker: data.ticker,
        predicted_log_return: data.predicted_log_return,
        direction: data.direction,
        timestamp: new Date().toISOString(),
        confidence: this.calculateConfidence(data.predicted_log_return)
      };

      // Cache the prediction
      this.cache.set(ticker, {
        ...prediction,
        fetchedAt: Date.now()
      });

      return prediction;
    } catch (error) {
      console.error(`Error fetching prediction for ${ticker}:`, error);
      return null;
    }
  }

  /**
   * Fetch predictions for multiple tickers in parallel
   */
  async getPredictions(tickers: string[]): Promise<PredictionResult[]> {
    const promises = tickers.map(ticker => this.getPrediction(ticker));
    const results = await Promise.all(promises);
    return results.filter((r): r is PredictionResult => r !== null);
  }

  /**
   * Calculate confidence percentage (0-100) from log return
   * Larger absolute values = higher confidence
   */
  private calculateConfidence(logReturn: number): number {
    const absReturn = Math.abs(logReturn);
    // Map log return to confidence: 0.001 -> 10%, 0.002 -> 20%, etc.
    // Cap at 95% to avoid overconfidence
    const confidence = Math.min(95, absReturn * 10000);
    return Math.max(10, confidence); // Minimum 10% confidence
  }

  /**
   * Clear cache for a specific ticker or all tickers
   */
  clearCache(ticker?: string): void {
    if (ticker) {
      this.cache.delete(ticker);
    } else {
      this.cache.clear();
    }
  }

  /**
   * Check if a prediction is cached and still fresh
   */
  isCached(ticker: string): boolean {
    const cached = this.cache.get(ticker);
    return cached !== undefined && Date.now() - cached.fetchedAt < CACHE_DURATION_MS;
  }
}

export const predictionService = new PredictionService();
export type { PredictionResult };
