import React, { useState, useEffect } from 'react';
import './StatsPage.css';

interface StatsPageProps {
  onBack: () => void;
}

interface TickerPerformance {
  ticker: string;
  avgIC: number;
  avgDirAcc: number;
  avgSharpe: number;
  avgMaxDD: number;
  status: string;
}

// Real performance data from LightGBM walk-forward backtest
const TICKER_PERFORMANCE: TickerPerformance[] = [
  { ticker: 'EUR/USD', avgIC: 0.2572, avgDirAcc: 0.5894, avgSharpe: 3.4997, avgMaxDD: -0.1439, status: 'Excellent' },
  { ticker: 'GBP/USD', avgIC: 0.2627, avgDirAcc: 0.5613, avgSharpe: 2.3056, avgMaxDD: -0.1456, status: 'Good' },
  { ticker: 'USD/JPY', avgIC: 0.1839, avgDirAcc: 0.5580, avgSharpe: 2.0283, avgMaxDD: -0.2102, status: 'Good' },
  { ticker: 'USD/CHF', avgIC: 0.3165, avgDirAcc: 0.6092, avgSharpe: 3.9841, avgMaxDD: -0.1718, status: 'Excellent' },
  { ticker: 'USD/CAD', avgIC: 0.1689, avgDirAcc: 0.5552, avgSharpe: 2.1149, avgMaxDD: -0.2792, status: 'Good' },
  { ticker: 'AUD/USD', avgIC: 0.1835, avgDirAcc: 0.4663, avgSharpe: 2.1147, avgMaxDD: -0.0842, status: 'Weak' },
  { ticker: 'NZD/USD', avgIC: 0.2294, avgDirAcc: 0.5803, avgSharpe: 3.0635, avgMaxDD: -0.1884, status: 'Excellent' },
  { ticker: 'EUR/MAD', avgIC: 0.3270, avgDirAcc: 0.5373, avgSharpe: 2.6422, avgMaxDD: -0.0262, status: 'Excellent' },
  { ticker: 'EUR/RUB', avgIC: 0.2569, avgDirAcc: 0.5656, avgSharpe: 1.6846, avgMaxDD: -0.7025, status: 'Moderate' },
  { ticker: 'RUB/USD', avgIC: 0.1450, avgDirAcc: 0.5255, avgSharpe: -0.0342, avgMaxDD: -2.1960, status: 'Bad' },
];

const METRIC_INFO = {
  sharpe: "Sharpe Ratio measures risk-adjusted returns. >2.0 is excellent in quant trading, >3.0 is institutional grade.",
  ic: "Information Coefficient (IC) measures predictive power. IC >0.05 indicates strong signal, >0.20 is exceptional.",
  dirAcc: "Directional Accuracy shows how often the model predicts the correct price movement. >55% is profitable after costs.",
  maxDD: "Maximum Drawdown shows the largest peak-to-trough decline. Lower is better. <-0.20 indicates good risk control."
};

const calculateOverallStats = () => {
  const alphaModels = TICKER_PERFORMANCE.filter(t => t.status.includes('Excellent')).length;
  const avgSharpe = TICKER_PERFORMANCE.reduce((sum, t) => sum + t.avgSharpe, 0) / TICKER_PERFORMANCE.length;
  const avgIC = TICKER_PERFORMANCE.reduce((sum, t) => sum + t.avgIC, 0) / TICKER_PERFORMANCE.length;
  
  return {
    modelsDeployed: TICKER_PERFORMANCE.length,
    alphaModels,
    avgSharpe: avgSharpe.toFixed(2),
    avgIC: (avgIC * 100).toFixed(1),
    activeTickers: TICKER_PERFORMANCE.length,
  };
};

export const StatsPage: React.FC<StatsPageProps> = ({ onBack }) => {
  const overallStats = calculateOverallStats();
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onBack();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        window.scrollBy({ top: -100, behavior: 'smooth' });
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        window.scrollBy({ top: 100, behavior: 'smooth' });
      }
    };
    
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.stat-card')) {
        setSelectedMetric(null);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    document.addEventListener('click', handleClickOutside);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('click', handleClickOutside);
    };
  }, [onBack]);

  return (
    <div className="stats-container">
      <div className="stats-content">
        <div className="stats-header">
          <div className="header-title">
            <span className="bracket">{'['}</span>
            <span className="title-text">PIPELINE PERFORMANCE METRICS</span>
            <span className="bracket">{']'}</span>
          </div>
          <button className="back-button" onClick={onBack}>
            <span className="back-icon">←</span> BACK TO MENU
          </button>
        </div>

        <div className="stats-grid">
          <div className="stat-card" onClick={() => setSelectedMetric('sharpe')} style={{ cursor: 'pointer' }}>
            <div className="stat-icon">📈</div>
            <div className="stat-value">{overallStats.avgSharpe}</div>
            <div className="stat-label">Avg Sharpe Ratio</div>
            {selectedMetric === 'sharpe' && (
              <div className="metric-trivia">{METRIC_INFO.sharpe}</div>
            )}
            <div className="stat-bar">
              <div className="stat-bar-fill" style={{ width: `${Math.min(parseFloat(overallStats.avgSharpe) * 20, 100)}%` }}></div>
            </div>
          </div>

          <div className="stat-card" onClick={() => setSelectedMetric('ic')} style={{ cursor: 'pointer' }}>
            <div className="stat-icon">🎯</div>
            <div className="stat-value">{overallStats.avgIC}%</div>
            <div className="stat-label">Avg IC</div>
            {selectedMetric === 'ic' && (
              <div className="metric-trivia">{METRIC_INFO.ic}</div>
            )}
            <div className="stat-bar">
              <div className="stat-bar-fill stat-info" style={{ width: `${overallStats.avgIC}%` }}></div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">⭐</div>
            <div className="stat-value">{overallStats.alphaModels}</div>
            <div className="stat-label">Excellent Models</div>
            <div className="stat-bar">
              <div className="stat-bar-fill stat-good" style={{ width: `${(overallStats.alphaModels / overallStats.modelsDeployed) * 100}%` }}></div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">💹</div>
            <div className="stat-value">{overallStats.activeTickers}</div>
            <div className="stat-label">Active Tickers</div>
            <div className="stat-bar">
              <div className="stat-bar-fill stat-info" style={{ width: '100%' }}></div>
            </div>
          </div>
        </div>

        <div className="performance-section">
          <div className="section-title">
            <span className="section-border">╔═══════════════════════════════════════╗</span>
          </div>
          <div className="section-subtitle">
            <span className="section-border">║</span>
            <span className="section-text">   MODEL PERFORMANCE BY TICKER</span>
            <span className="section-border">         ║</span>
          </div>
          <div className="section-title">
            <span className="section-border">╚═══════════════════════════════════════╝</span>
          </div>

          <div className="ticker-performance">
            {TICKER_PERFORMANCE.map((item) => {
              const getStatusColor = (status: string) => {
                if (status.includes('Excellent') || status.includes('Good')) return 'status-excellent';
                if (status.includes('Moderate')) return 'status-moderate';
                return 'status-poor';
              };

              return (
                <div key={item.ticker} className="ticker-row">
                  <div className="ticker-name">{item.ticker}</div>
                  <div className="ticker-metrics">
                    <span className="metric-item" title={METRIC_INFO.sharpe}>
                      <span className="metric-label">Sharpe:</span> 
                      <span className={`metric-value ${getStatusColor(item.status)}`}>
                        {item.avgSharpe.toFixed(2)}
                      </span>
                    </span>
                    <span className="metric-item" title={METRIC_INFO.ic}>
                      <span className="metric-label">IC:</span> 
                      <span className="metric-value">{(item.avgIC * 100).toFixed(1)}%</span>
                    </span>
                    <span className="metric-item" title={METRIC_INFO.dirAcc}>
                      <span className="metric-label">Dir Acc:</span> 
                      <span className="metric-value">{(item.avgDirAcc * 100).toFixed(1)}%</span>
                    </span>
                    <span className="metric-item" title={METRIC_INFO.maxDD}>
                      <span className="metric-label">Max DD:</span> 
                      <span className="metric-value">{item.avgMaxDD.toFixed(2)}</span>
                    </span>
                  </div>
                  <div className="ticker-accuracy">
                    <div className="accuracy-bar">
                      <div 
                        className={`accuracy-bar-fill ${getStatusColor(item.status)}`}
                        style={{ width: `${Math.max(8, Math.min(item.avgSharpe * 20, 100))}%` }}
                      ></div>
                    </div>
                  </div>
                  <div className={`ticker-status ${getStatusColor(item.status)}`}>
                    {item.status}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="stats-footer">
          <div className="footer-info">
            <span className="footer-label">[STATUS]</span> All systems operational
          </div>
          <div className="footer-hint">
            <span className="hint-key">ESC</span> Return to menu • 
            <span className="hint-key">↑↓</span> Scroll
          </div>
        </div>
      </div>
      <div className="crt-effect"></div>
    </div>
  );
};
