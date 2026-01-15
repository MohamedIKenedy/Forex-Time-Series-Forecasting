import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const startStreaming = async () => {
  try {
    const response = await api.post('/stream/start_streaming');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to start streaming: ${error}`);
  }
};

export const startInstantStreaming = async () => {
  try {
    const response = await api.post('/stream/start_instant_streaming');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to start instant streaming: ${error}`);
  }
};

export const ensureInstantStreaming = async () => {
  // If another streaming mode is running, the backend won't switch modes unless we stop first.
  try {
    await stopStreaming();
  } catch {
    // Ignore: it may already be stopped.
  }
  return startInstantStreaming();
};

export const stopStreaming = async () => {
  try {
    const response = await api.post('/stream/stop_streaming');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to stop streaming: ${error}`);
  }
};

export const getForexData = async (ticker: string, period: string = '1d') => {
  try {
    const response = await api.get(`/stream/data/${ticker}`, {
      params: { period }
    });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch data for ${ticker}: ${error}`);
  }
};

export const getStreamingStatus = async () => {
  try {
    const response = await api.get('/stream/status');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch streaming status: ${error}`);
  }
};

export const getKafkaDiagram = async () => {
  try {
    const response = await api.get('/kafka/diagram');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch kafka diagram: ${error}`);
  }
};

export const getKafkaHealth = async () => {
  try {
    const response = await api.get('/kafka/health');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch kafka health: ${error}`);
  }
};

export const getKafkaTopics = async (prefix?: string) => {
  try {
    const response = await api.get('/kafka/topics', {
      params: prefix ? { prefix } : undefined,
    });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch kafka topics: ${error}`);
  }
};

export const getInference = async (ticker: string, lookback: number = 200) => {
  try {
    const response = await api.get(`/inference/${ticker}`, {
      params: { lookback }
    });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch inference for ${ticker}: ${error}`);
  }
};

export const getInferenceMetadata = async (ticker: string) => {
  try {
    const response = await api.get(`/inference/${ticker}/metadata`);
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch metadata for ${ticker}: ${error}`);
  }
};

export const getAvailableTickers = async () => {
  try {
    const response = await api.get('/data/tickers');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch available tickers: ${error}`);
  }
};
