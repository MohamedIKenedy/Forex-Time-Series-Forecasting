import React, { useState, useEffect, useRef } from 'react';
import './TickersPage.css';

interface TickersPageProps {
  onBack: () => void;
  onSelectTicker?: (ticker: string) => void;
}

const availableTickers = [
  { symbol: 'EUR/USD', name: 'Euro / US Dollar', status: 'active', accuracy: 58.9 },
  { symbol: 'GBP/USD', name: 'British Pound / US Dollar', status: 'active', accuracy: 56.1 },
  { symbol: 'USD/JPY', name: 'US Dollar / Japanese Yen', status: 'active', accuracy: 55.8 },
  { symbol: 'USD/CHF', name: 'US Dollar / Swiss Franc', status: 'active', accuracy: 60.9 },
  { symbol: 'USD/CAD', name: 'US Dollar / Canadian Dollar', status: 'active', accuracy: 55.5 },
  { symbol: 'AUD/USD', name: 'Australian Dollar / US Dollar', status: 'active', accuracy: 46.6 },
  { symbol: 'NZD/USD', name: 'New Zealand Dollar / US Dollar', status: 'active', accuracy: 58.0 },
  { symbol: 'EUR/MAD', name: 'Euro / Moroccan Dirham', status: 'active', accuracy: 53.7 },
  { symbol: 'EUR/RUB', name: 'Euro / Russian Ruble', status: 'active', accuracy: 56.6 },
  { symbol: 'RUB/USD', name: 'Russian Ruble / US Dollar', status: 'active', accuracy: 52.5 },
];

export const TickersPage: React.FC<TickersPageProps> = ({ onBack, onSelectTicker }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [filter, setFilter] = useState('');

  const filteredTickers = availableTickers.filter(ticker =>
    ticker.symbol.toLowerCase().includes(filter.toLowerCase()) ||
    ticker.name.toLowerCase().includes(filter.toLowerCase())
  );

  const refs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onBack();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + filteredTickers.length) % filteredTickers.length);
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % filteredTickers.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredTickers[selectedIndex]) {
          onSelectTicker?.(filteredTickers[selectedIndex].symbol);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onBack, selectedIndex, filteredTickers, onSelectTicker]);

  useEffect(() => {
    if (refs.current[selectedIndex]) {
      refs.current[selectedIndex]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [selectedIndex]);

  useEffect(() => {
    if (selectedIndex >= filteredTickers.length) {
      setSelectedIndex(0);
    }
  }, [filteredTickers.length]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return '#00ff41';
      case 'inactive':
        return '#ff4444';
      default:
        return '#ffaa00';
    }
  };

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 55) return '#00ff41';
    if (accuracy >= 50) return '#ffaa00';
    return '#ff4444';
  };

  return (
    <div className="tickers-container">
      <div className="tickers-content">
        <div className="tickers-header">
          <div className="header-title">
            <span className="bracket">{'['}</span>
            <span className="title-text">AVAILABLE FOREX PAIRS</span>
            <span className="bracket">{']'}</span>
          </div>
          <button className="back-button" onClick={onBack}>
            <span className="back-icon">←</span> BACK TO MENU
          </button>
        </div>

        <div className="search-container">
          <div className="search-label">SEARCH:</div>
          <input
            type="text"
            className="search-input"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Enter ticker symbol or name..."
            autoFocus
          />
          <div className="search-icon">🔍</div>
        </div>

        <div className="tickers-info">
          <div className="info-box">
            <span className="info-label">Total Pairs:</span>
            <span className="info-value">{availableTickers.length}</span>
          </div>
          <div className="info-box">
            <span className="info-label">Active:</span>
            <span className="info-value">{availableTickers.filter(t => t.status === 'active').length}</span>
          </div>
          <div className="info-box">
            <span className="info-label">Avg Accuracy:</span>
            <span className="info-value">
              {(availableTickers.reduce((sum, t) => sum + t.accuracy, 0) / availableTickers.length).toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="section-divider">
          <span className="divider-line">═══════════════════════════════════════════════════════</span>
        </div>

        <div className="tickers-list">
          {filteredTickers.map((ticker, index) => (
            <div
              key={ticker.symbol}
              ref={(el) => {refs.current[index] = el;}}
              className={`ticker-item ${selectedIndex === index ? 'selected' : ''}`}
              onClick={() => {
                setSelectedIndex(index);
                onSelectTicker?.(ticker.symbol);
              }}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <div className="ticker-selector">
                {selectedIndex === index ? '►' : ' '}
              </div>
              <div className="ticker-info">
                <div className="ticker-symbol">{ticker.symbol}</div>
                <div className="ticker-name">{ticker.name}</div>
              </div>
              <div className="ticker-stats">
                <div className="ticker-status">
                  <span
                    className="status-indicator"
                    style={{ color: getStatusColor(ticker.status) }}
                  >
                    ●
                  </span>
                  <span className="status-text">{ticker.status.toUpperCase()}</span>
                </div>
                <div className="ticker-accuracy">
                  <span className="accuracy-label">Accuracy:</span>
                  <span
                    className="accuracy-value"
                    style={{ color: getAccuracyColor(ticker.accuracy) }}
                  >
                    {ticker.accuracy}%
                  </span>
                </div>
              </div>
              <div className="ticker-arrow">
                {selectedIndex === index ? '→' : ''}
              </div>
            </div>
          ))}
        </div>

        {filteredTickers.length === 0 && (
          <div className="no-results">
            <div className="no-results-icon">⚠</div>
            <div className="no-results-text">No tickers found matching "{filter}"</div>
          </div>
        )}

        <div className="tickers-footer">
          <div className="footer-info">
            <span className="footer-label">[INFO]</span> Select a ticker to view details
          </div>
          <div className="footer-hints">
            <span className="hint-key">↑↓</span> Navigate
            <span className="hint-key">ENTER</span> Select
            <span className="hint-key">ESC</span> Back
          </div>
        </div>
      </div>
      <div className="crt-effect"></div>
    </div>
  );
};
