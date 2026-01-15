import React, { useEffect, useRef, useState, useCallback } from 'react';
import type { PlotData, InferenceData } from '../types';
import { getInference } from '../api';
import './Chart.css';

interface ChartProps {
  data: PlotData;
  onTickerChange?: (ticker: string) => void;
  onPeriodChange?: (period: string) => void;
  currentPeriod?: string;
}

const TICKERS = [
  'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'USDCHF=X', 
  'USDCAD=X', 'AUDUSD=X', 'NZDUSD=X', 'EURMAD=X',
  'EURRUB=X', 'RUBUSD=X'
];

export const Chart: React.FC<ChartProps> = ({ data, onTickerChange, onPeriodChange, currentPeriod = '1d' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; price: number; date: string; isPrediction?: boolean; inference?: InferenceData } | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);
  const [cursorPos, setCursorPos] = useState<{ x: number; y: number } | null>(null);
  const [prediction, setPrediction] = useState<InferenceData | null>(null);
  const showPrediction = currentPeriod !== '1d';

  const PRICE_DECIMALS = 6;
  const POINT_RADIUS = 2; // keep markers tiny so the line looks smooth

  // Fetch prediction when ticker changes
  const fetchPrediction = useCallback(async () => {
    if (!data?.ticker) return;
    try {
      const result = await getInference(data.ticker);
      setPrediction(result);
    } catch (error) {
      console.error('Failed to fetch prediction:', error);
      setPrediction(null);
    }
  }, [data?.ticker]);

  useEffect(() => {
    fetchPrediction();
  }, [fetchPrediction]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (!data?.prices?.length || !data?.dates?.length) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    // Set canvas size
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.fillStyle = '#0a0e27';
    ctx.fillRect(0, 0, width, height);

    const leftPadding = 240;
    const rightPadding = 100;
    const topPadding = 100;
    const bottomPadding = 120;

    const parsedTimestamps = data.dates.map((date, idx) => {
      const ts = Date.parse(date);
      return Number.isFinite(ts) ? ts : idx;
    });

    const minTs = Math.min(...parsedTimestamps);
    const maxTs = Math.max(...parsedTimestamps);
    const avgInterval = parsedTimestamps.length > 1
        ? (parsedTimestamps[parsedTimestamps.length - 1] - parsedTimestamps[0]) / (parsedTimestamps.length - 1)
      : 0;
      const futureTs = showPrediction && prediction && parsedTimestamps.length > 0
        ? parsedTimestamps[parsedTimestamps.length - 1] + (avgInterval || 60000)
      : null;
    const effectiveMaxTs = futureTs ? Math.max(maxTs, futureTs) : maxTs;
    const tsRange = Math.max(1, effectiveMaxTs - minTs);
    const toX = (ts: number) => leftPadding + ((ts - minTs) / tsRange) * (width - leftPadding - rightPadding);

    const minRawPrice = Math.min(...data.prices);
    const maxRawPrice = Math.max(...data.prices);
    const rawRange = Math.max(0, maxRawPrice - minRawPrice);
    const padding = rawRange === 0 ? Math.max(1e-6, maxRawPrice * 0.0001) : rawRange * 0.015;
    const minPrice = minRawPrice - padding;
    const maxPrice = maxRawPrice + padding;
    const priceRange = Math.max(1e-9, maxPrice - minPrice);

    // Draw grid lines
    ctx.strokeStyle = '#1a1f3a';
    ctx.lineWidth = 2;
    const bands = 5;
    for (let i = 0; i <= bands; i++) {
      const y = topPadding + (i * (height - bottomPadding - topPadding)) / bands;
      ctx.beginPath();
      ctx.moveTo(leftPadding, y);
      ctx.lineTo(width - rightPadding, y);
      ctx.stroke();
    }

    // Draw price labels (Y-axis) with light padding to mimic Yahoo ranges.
    ctx.fillStyle = '#4ade80';
    ctx.font = '22px "Courier New", monospace';
    ctx.textAlign = 'right';
    for (let i = 0; i <= bands; i++) {
      const price = maxPrice - (i * priceRange) / bands;
      const y = topPadding + (i * (height - bottomPadding - topPadding)) / bands;
      ctx.fillText(price.toFixed(PRICE_DECIMALS), leftPadding - 16, y + 8);
    }

    // Draw date labels (X-axis) spaced by actual time delta (UTC) to mirror Yahoo's timeline.
    ctx.fillStyle = '#94a3b8';
    ctx.font = '20px "Courier New", monospace';
    ctx.textAlign = 'center';
    const showTimeLabels = !['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'].includes(currentPeriod);
    const labelCount = Math.min(6, data.dates.length);
    const timeFormatter = new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'UTC' });
    const dateFormatter = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: '2-digit', timeZone: 'UTC' });

    for (let i = 0; i < labelCount; i++) {
      const ratio = labelCount === 1 ? 0 : i / (labelCount - 1);
      const ts = minTs + ratio * tsRange;
      const x = toX(ts);
      const dateObj = new Date(ts);
      const dateStr = dateFormatter.format(dateObj);
      ctx.fillText(dateStr, x, height - bottomPadding + 30);
      if (showTimeLabels) {
        ctx.fillStyle = '#64748b';
        ctx.font = '18px "Courier New", monospace';
        ctx.fillText(timeFormatter.format(dateObj), x, height - bottomPadding + 54);
        ctx.font = '20px "Courier New", monospace';
        ctx.fillStyle = '#94a3b8';
      }
    }

    // Draw line chart
    ctx.strokeStyle = data.streaming ? '#22c55e' : '#3b82f6';
    ctx.lineWidth = 4;
    ctx.beginPath();

    const points = data.prices.map((price, index) => {
      const ts = parsedTimestamps[index];
      const x = toX(ts);
      const y = height - bottomPadding - ((price - minPrice) / priceRange) * (height - topPadding - bottomPadding);
      return { x, y, ts, price, date: data.dates[index] };
    });

    points.forEach((pt, index) => {
      if (index === 0) {
        ctx.moveTo(pt.x, pt.y);
      } else {
        ctx.lineTo(pt.x, pt.y);
      }
    });

    ctx.stroke();

    // Draw area fill
    ctx.lineTo(width - rightPadding, height - bottomPadding);
    ctx.lineTo(leftPadding, height - bottomPadding);
    ctx.closePath();
    const gradient = ctx.createLinearGradient(0, topPadding, 0, height - bottomPadding);
    gradient.addColorStop(0, data.streaming ? 'rgba(34, 197, 94, 0.15)' : 'rgba(59, 130, 246, 0.15)');
    gradient.addColorStop(1, 'rgba(10, 14, 39, 0)');
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw points
    ctx.fillStyle = data.streaming ? '#22c55e' : '#3b82f6';
    points.forEach((pt) => {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, POINT_RADIUS, 0, Math.PI * 2);
      ctx.fill();
    });

    // Draw prediction extension line if available
    if (showPrediction && prediction && points.length > 1 && futureTs !== null) {
      const lastPrice = data.prices[data.prices.length - 1];
      const predictedPrice = lastPrice * Math.exp(prediction.predicted_log_return);

      const predX = toX(futureTs);
      const rawPredY = height - bottomPadding - ((predictedPrice - minPrice) / priceRange) * (height - topPadding - bottomPadding);
      const predY = Math.max(topPadding + 10, Math.min(rawPredY, height - bottomPadding - 10));

      const lastX = toX(parsedTimestamps[parsedTimestamps.length - 1]);
      const lastY = points[points.length - 1].y;

      const predColor = prediction.direction === 'UP' ? '#22c55e' : prediction.direction === 'DOWN' ? '#ef4444' : '#f59e0b';
      ctx.strokeStyle = predColor;
      ctx.lineWidth = 4;
      ctx.setLineDash([8, 6]);
      ctx.beginPath();
      ctx.moveTo(lastX, lastY);
      ctx.lineTo(predX, predY);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = predColor;
      ctx.beginPath();
      ctx.arc(predX, predY, POINT_RADIUS + 2, 0, Math.PI * 2);
      ctx.fill();
    }

    // Draw crosshair if hovering
    if (mousePos) {
      ctx.strokeStyle = '#4ade8040';
      ctx.lineWidth = 2;
      ctx.setLineDash([10, 10]);
      
      // Vertical line
      ctx.beginPath();
      ctx.moveTo(mousePos.x, topPadding);
      ctx.lineTo(mousePos.x, height - bottomPadding);
      ctx.stroke();
      
      // Horizontal line
      ctx.beginPath();
      ctx.moveTo(leftPadding, mousePos.y);
      ctx.lineTo(width - rightPadding, mousePos.y);
      ctx.stroke();
      
      ctx.setLineDash([]);
    }

    // Draw hovered point highlight
    if (hoveredPoint) {
      ctx.strokeStyle = '#4ade80';
      ctx.fillStyle = '#0a0e27';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(hoveredPoint.x, hoveredPoint.y, 10, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }

    // Draw title and stats
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 28px "Courier New", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`${data.ticker}`, 20, 44);
    
    ctx.fillStyle = data.streaming ? '#ef4444' : '#3b82f6';
    ctx.font = '22px "Courier New", monospace';
    ctx.fillText(data.streaming ? 'LIVE' : 'HISTORICAL', 20, 76);

    // Draw current price - prioritize latest streaming data
    const currentPrice = data.latest?.close ?? data.prices[data.prices.length - 1];
    ctx.fillStyle = '#4ade80';
    ctx.textAlign = 'right';
    ctx.font = 'bold 28px "Courier New", monospace';
    ctx.fillText(`${currentPrice.toFixed(PRICE_DECIMALS)}`, width - 20, 44);

  }, [data, hoveredPoint, mousePos, prediction, currentPeriod]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    
    const displayX = e.clientX - rect.left;
    const displayY = e.clientY - rect.top;

    setMousePos({ x, y });
    setCursorPos({ x: displayX, y: displayY });

    const width = canvas.width;
    const height = canvas.height;
    const leftPadding = 240;
    const rightPadding = 100;
    const topPadding = 100;
    const bottomPadding = 120;

    const parsedTimestamps = data.dates.map((date, idx) => {
      const ts = Date.parse(date);
      return Number.isFinite(ts) ? ts : idx;
    });

    const minTs = Math.min(...parsedTimestamps);
    const maxTs = Math.max(...parsedTimestamps);
    const avgInterval = parsedTimestamps.length > 1
      ? (parsedTimestamps[parsedTimestamps.length - 1] - parsedTimestamps[0]) / (parsedTimestamps.length - 1)
      : 0;
    const futureTs = prediction && parsedTimestamps.length > 0
      ? parsedTimestamps[parsedTimestamps.length - 1] + (avgInterval || 60000)
      : null;
    const effectiveMaxTs = futureTs ? Math.max(maxTs, futureTs) : maxTs;
    const tsRange = Math.max(1, effectiveMaxTs - minTs);
    const toX = (ts: number) => leftPadding + ((ts - minTs) / tsRange) * (width - leftPadding - rightPadding);

    const minRawPrice = Math.min(...data.prices);
    const maxRawPrice = Math.max(...data.prices);
    const rawRange = Math.max(0, maxRawPrice - minRawPrice);
    const padding = rawRange === 0 ? Math.max(1e-6, maxRawPrice * 0.0001) : rawRange * 0.015;
    const minPrice = minRawPrice - padding;
    const maxPrice = maxRawPrice + padding;
    const priceRange = Math.max(1e-9, maxPrice - minPrice);

    let nearestIndex = -1;
    let minDistance = Infinity;

    // Check if hovering over prediction point first
    if (showPrediction && prediction && data.prices.length > 1 && futureTs !== null) {
      const lastPrice = data.prices[data.prices.length - 1];
      const predictedPrice = lastPrice * Math.exp(prediction.predicted_log_return);

      const predX = toX(futureTs);
      const rawPredY = height - bottomPadding - ((predictedPrice - minPrice) / priceRange) * (height - topPadding - bottomPadding);
      const predY = Math.max(topPadding + 10, Math.min(rawPredY, height - bottomPadding - 10));

      const predDistance = Math.sqrt((x - predX) ** 2 + (y - predY) ** 2);

      if (predDistance < 30) {
        setHoveredPoint({
          x: predX,
          y: predY,
          price: predictedPrice,
          date: futureTs ? new Date(futureTs).toISOString() : '',
          isPrediction: true,
          inference: prediction
        });
        return;
      }
    }

    data.prices.forEach((price, index) => {
      const ts = parsedTimestamps[index];
      const pointX = toX(ts);
      const pointY = height - bottomPadding - ((price - minPrice) / priceRange) * (height - topPadding - bottomPadding);
      const distance = Math.sqrt((x - pointX) ** 2 + (y - pointY) ** 2);

      if (distance < minDistance && distance < 40) {
        minDistance = distance;
        nearestIndex = index;
      }
    });

    if (nearestIndex >= 0) {
      const ts = parsedTimestamps[nearestIndex];
      const pointX = toX(ts);
      const pointY = height - bottomPadding - ((data.prices[nearestIndex] - minPrice) / priceRange) * (height - topPadding - bottomPadding);

      setHoveredPoint({
        x: pointX,
        y: pointY,
        price: data.prices[nearestIndex],
        date: data.dates[nearestIndex]
      });
    } else {
      setHoveredPoint(null);
    }
  };

  const handleMouseLeave = () => {
    setHoveredPoint(null);
    setMousePos(null);
    setCursorPos(null);
  };

  return (
    <div className="chart-container">
      <div className="chart-controls" onClick={(e) => e.stopPropagation()}>
        <span className="chart-label">SELECT TICKER:</span>
        <select 
          className="ticker-select" 
          value={data.ticker}
          onChange={(e) => onTickerChange?.(e.target.value)}
          onClick={(e) => e.stopPropagation()}
        >
          {TICKERS.map(ticker => (
            <option key={ticker} value={ticker}>{ticker}</option>
          ))}
        </select>
        
        <span className="chart-label" style={{ marginLeft: '20px' }}>TIME RANGE:</span>
        <select 
          className="period-select" 
          value={currentPeriod}
          onChange={(e) => onPeriodChange?.(e.target.value)}
          onClick={(e) => e.stopPropagation()}
        >
          <option value="1d">1 Day (1min)</option>
          <option value="5d">5 Days (5min)</option>
          <option value="1mo">1 Month (daily)</option>
          <option value="3mo">3 Months (daily)</option>
          <option value="6mo">6 Months (daily)</option>
          <option value="1y">1 Year (daily)</option>
        </select>
      </div>
      <canvas 
        ref={canvasRef} 
        width={2400} 
        height={900}
        style={{ width: '1200px', height: '450px' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      />
      {hoveredPoint && cursorPos && (
        <div 
          className="tooltip"
          style={{
            left: `${cursorPos.x + 20}px`,
            top: `${cursorPos.y - 60}px`
          }}
        >
          <div className="tooltip-price">{hoveredPoint.price.toFixed(PRICE_DECIMALS)}</div>
          {hoveredPoint.isPrediction && hoveredPoint.inference ? (
            <>
              <div className="tooltip-date">
                {`${hoveredPoint.inference.direction} | ${new Date(hoveredPoint.date).toLocaleDateString('en-US')}`}
              </div>
              <div className="tooltip-date">
                {`Model output: ${hoveredPoint.inference.predicted_log_return.toFixed(6)} log return`}
              </div>
            </>
          ) : (
            <div className="tooltip-date">
              {`${new Date(hoveredPoint.date).toLocaleString('en-US', { timeZone: 'UTC' })} UTC`}
            </div>
          )}
        </div>
      )}
      <div className="chart-info">
        <span className="data-points">[{data.prices.length} POINTS]</span>
        <span className="date-range">
          {new Date(data.dates[0]).toLocaleString('en-US', { timeZone: 'UTC' })} → {new Date(data.dates[data.dates.length - 1]).toLocaleString('en-US', { timeZone: 'UTC' })}
        </span>
      </div>
    </div>
  );
};
