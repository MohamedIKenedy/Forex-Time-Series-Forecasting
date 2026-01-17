import React, { useState, useEffect, useCallback } from 'react';
import './LandingPage.css';

interface LandingPageProps {
  onNavigate: (page: 'terminal' | 'stats' | 'tickers') => void;
}

const OPTIONS = [
  { id: 'terminal', label: 'Terminal', description: 'Interactive command interface' },
  { id: 'stats', label: 'Pipeline Stats', description: 'View performance metrics' },
  { id: 'tickers', label: 'Available Tickers', description: 'Browse forex pairs' }
] as const;

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
  const [selectedOption, setSelectedOption] = useState(0);
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 530);

    return () => clearInterval(cursorInterval);
  }, []);

  const handleOptionClick = useCallback((index: number) => {
    setSelectedOption(index);
    onNavigate(OPTIONS[index].id as 'terminal' | 'stats' | 'tickers');
  }, [onNavigate]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedOption(prev => (prev - 1 + OPTIONS.length) % OPTIONS.length);
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedOption(prev => (prev + 1) % OPTIONS.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        onNavigate(OPTIONS[selectedOption].id as 'terminal' | 'stats' | 'tickers');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedOption, onNavigate]);

  return (
    <div className="landing-container">
      <div className="landing-content">
        <div className="landing-header">
          <div className="ascii-art">
            <pre>{`
 ╔═══════════════════════════════════════════════╗
 ║                                               ║
 ║                Mohamed Ifqir                  ║
 ║                                               ║
 ╚═══════════════════════════════════════════════╝
            `}</pre>
          </div>
          <div className="subtitle">
            <span className="bracket">{'['}</span>
            <span className="subtitle-text">FOREX FORECASTING PLATFORM</span>
            <span className="bracket">{']'}</span>
          </div>
          <div className="system-info">
            <div className="info-line">
              <span className="info-label">System:</span>
              <span className="info-value">ForexOS v2.0.1</span>
            </div>
            <div className="info-line">
              <span className="info-label">Status:</span>
              <span className="info-value status-online">● ONLINE</span>
            </div>
            <div className="info-line">
              <span className="info-label">Mode:</span>
              <span className="info-value">PRODUCTION</span>
            </div>
          </div>
        </div>

        <div className="menu-section">
          <div className="menu-title">
            <span className="menu-border">╔═══════════════════════════════════════╗</span>
          </div>
          <div className="menu-subtitle">
            <span className="menu-border">║</span>
            <span className="menu-text">   MAIN NAVIGATION INTERFACE</span>
            <span className="menu-border">          ║</span>
          </div>
          <div className="menu-title">
            <span className="menu-border">╚═══════════════════════════════════════╝</span>
          </div>

          <div className="options-container">
            {OPTIONS.map((option, index) => (
              <div
                key={option.id}
                className={`option-item ${selectedOption === index ? 'selected' : ''}`}
                onClick={() => handleOptionClick(index)}
                onMouseEnter={() => setSelectedOption(index)}
              >
                <div className="option-selector">
                  {selectedOption === index ? '►' : ' '}
                </div>
                <div className="option-content">
                  <div className="option-label">{option.label}</div>
                  <div className="option-description">{option.description}</div>
                </div>
                <div className="option-number">
                  {selectedOption === index && showCursor ? '█' : ' '}
                </div>
              </div>
            ))}
          </div>

          <div className="navigation-hint">
            <div className="hint-line">
              <span className="hint-key">↑↓</span> Navigate  
              <span className="hint-key">ENTER</span> Select  
              <span className="hint-key">CLICK</span> Choose
            </div>
          </div>
        </div>

        <div className="landing-footer">
          <div className="scanline"></div>
          <div className="footer-text">
            <span className="footer-label">[SYSTEM]</span> Press any key to continue...
          </div>
        </div>
      </div>
      <div className="crt-effect"></div>
      <div className="noise"></div>
    </div>
  );
};
