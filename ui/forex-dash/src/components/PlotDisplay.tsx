import React from 'react';
import Plot from 'react-plotly.js';
import './PlotDisplay.css';

interface PlotDisplayProps {
  ticker?: string;
  data?: {
    x: number[];
    y: number[];
  };
  onClose: () => void;
}

export const PlotDisplay: React.FC<PlotDisplayProps> = ({ ticker, data, onClose }) => {
  if (!data) {
    return (
      <div className="plot-container">
        <div className="plot-header">
          <h3>{ticker || 'Plot'}</h3>
          <button onClick={onClose} className="close-btn">×</button>
        </div>
        <div className="plot-content">
          <p>No data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="plot-container">
      <div className="plot-header">
        <h3>{ticker || 'Plot'}</h3>
        <button onClick={onClose} className="close-btn">×</button>
      </div>
      <div className="plot-content">
        <Plot
          data={[
            {
              x: data.x,
              y: data.y,
              type: 'scatter',
              mode: 'lines',
              name: ticker,
              line: { color: '#58a6ff', width: 2 },
            },
          ]}
          layout={{
            title: `${ticker} Price Chart`,
            xaxis: { title: 'Time' },
            yaxis: { title: 'Price' },
            plot_bgcolor: '#0d1117',
            paper_bgcolor: '#0d1117',
            font: { color: '#c9d1d9' },
            margin: { l: 50, r: 50, t: 50, b: 50 },
          }}
          config={{ responsive: true }}
          style={{ width: '100%', height: '100%' }}
        />
      </div>
    </div>
  );
};
