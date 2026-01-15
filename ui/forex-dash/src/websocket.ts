export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectInterval: number = 3000;
  private listeners: Set<(data: any) => void> = new Set();
  private pingTimer: number | null = null;
  private reconnectTimer: number | null = null;
  private shouldReconnect: boolean = true;

  connect() {
    // Make connect idempotent.
    this.shouldReconnect = true;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    // Clear any stale timers from previous connections.
    if (this.pingTimer != null) {
      window.clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
    if (this.reconnectTimer != null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    const ws = new WebSocket('ws://localhost:8000/stream/ws');
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      this.pingTimer = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        if (event.data === 'pong') {
          return;
        }
        const message = JSON.parse(event.data);
        if (message.type === 'price_update') {
          this.listeners.forEach(callback => callback(message));
        }
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      if (this.pingTimer != null) {
        window.clearInterval(this.pingTimer);
        this.pingTimer = null;
      }

      if (this.shouldReconnect) {
        this.reconnectTimer = window.setTimeout(() => this.connect(), this.reconnectInterval);
      }
    };

    this.ws = ws;
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer != null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.pingTimer != null) {
      window.clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
    this.ws = null;
  }

  subscribe(callback: (data: any) => void) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }
}

export const wsClient = new WebSocketClient();
