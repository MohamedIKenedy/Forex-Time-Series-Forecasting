export interface PlotData {
  ticker: string;
  dates: string[];
  prices: number[];
  streaming: boolean;
  period?: string;
  interval?: string;
  latest?: {
    close: number;
    timestamp: string;
    [key: string]: any;
  };
}

export interface TerminalOutput {
  id: string;
  content: string;
  type: 'command' | 'output' | 'error' | 'success';
  plotData?: PlotData;
  clearTerminal?: boolean;
}

export interface StreamingStatus {
  status: 'idle' | 'streaming' | 'stopped';
  tickers: string[];
  lastUpdate?: Date;
}

export interface InferenceData {
  ticker: string;
  predicted_log_return: number;
  direction: 'UP' | 'DOWN' | 'SIDEWAYS';
}
