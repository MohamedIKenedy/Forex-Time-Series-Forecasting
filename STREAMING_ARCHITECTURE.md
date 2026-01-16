# Real-Time Forex Streaming Architecture: Async and Kafka

## Table of Contents
1. [Overview](#overview)
2. [Concurrency Considerations](#concurrency-considerations)
3. [Hybrid Architecture Design](#hybrid-architecture-design)
4. [Why Kafka](#why-kafka)
5. [Architecture Components](#architecture-components)
6. [Kafka Data Flow](#kafka-data-flow)
7. [Performance Optimizations](#performance-optimizations)
8. [Production Deployment](#production-deployment)

---

## Overview

This architecture solves a fundamental Python web development challenge: integrating synchronous blocking I/O (HTTP requests to market data APIs) with asynchronous WebSocket broadcasting while maintaining horizontal scalability through Kafka.

### The Core Idea

The design separates blocking market-data polling from async WebSocket broadcasting and uses Kafka to decouple producers and consumers. Worker processes/threads are an implementation detail used to keep blocking I/O off the main async event loop; the system is driven by async broadcasts and durable Kafka topics.

Key benefits: partitioned caching for fast lookups, deduplication to reduce traffic, and Kafka-based pub/sub for horizontal scalability and replay.

---

## Concurrency Considerations

Blocking I/O (market-data polling, some Kafka client operations) is kept off the async event loop via lightweight worker processes or threads. The architecture favors clear separation: blocking work runs in workers, async I/O and WebSocket broadcasting run on the event loop, and Kafka decouples producers/consumers. Use of threads is an implementation detail and not the central design point.

---

## Architecture Components

High-level component summary (no heavy code):

The frontend is a React application that opens a single WebSocket per client; chart components subscribe to that connection and re-render when price updates arrive. A `ConnectionManager` component on the backend maintains those WebSocket sessions and performs asynchronous broadcasts to active clients. Market-data ingestion is the responsibility of a `StreamingService` which polls external APIs, applies fast deduplication, and publishes only new updates to Kafka topics keyed by ticker. Kafka itself acts as the durable message bus: partitioned topics provide ordering and replay guarantees while enabling fan-out to multiple downstream consumers. Consumer-side adapters (the Kafka bridge and similar consumers) subscribe to those topics and hand messages to lightweight stream utilities that update an in-memory, partitioned cache and schedule async broadcasts. In short: producers fetch and publish, Kafka stores and fans out, and consumers update cache and trigger broadcasts.

---

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React/TypeScript)                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │   Chart.tsx  │    │  WebSocket   │    │   App.tsx    │           │
│  │   Component  │◄───┤    Client    │◄───┤   Manager    │           │
│  └──────────────┘    └──────┬───────┘    └──────────────┘           │
└─────────────────────────────│───────────────────────────────────────┘
                              │ ws://localhost:8000/stream/ws
                              │
┌─────────────────────────────▼─────────────────────────────────────────┐
│                      FastAPI Backend (Python)                         │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    WebSocket Endpoint (/ws)                      │ │
│  │  • Accepts connections                                           │ │
│  │  • Sets event loop for async broadcasting                        │ │
│  │  • Handles ping/pong keepalive                                   │ │
│  └────────────────┬─────────────────────────────────────────────────┘ │
│                   │                                                   │
│  ┌────────────────▼──────────────────────────────────────────────┐    │
│  │            ConnectionManager (conn_management.py)             │    │
│  │  • Maintains active WebSocket connections                     │    │
│  │  • Broadcasts messages to all clients                         │    │
│  │  • Handles connection/disconnection lifecycle                 │    │
│  └────────────────┬──────────────────────────────────────────────┘    │
│                   │                                                   │
│  ┌────────────────▼──────────────────────────────────────────────┐    │
│  │          Stream Utilities (stream_utils.py)                   │    │
│  │  • update_cache_and_broadcast()                               │    │
│  │  • Partitioned data cache (ticker → period_interval → data)   │    │
│  │  • Kafka bridge management                                    │    │
│  └─────┬─────────────────────────────────────────────┬───────────┘    │
│        │                                             │                │
│  ┌─────▼──────────────────┐              ┌───────────▼─────────────┐  │
│  │  StreamingService      │              │   KafkaWebSocketBridge  │  │
│  │  (streaming_service.py)│              │   (kafka_bridge.py)     │  │
│  │                        │              │                         │  │
│  │  • stream_instant()    │              │  • Kafka consumer       │  │
│  │  • stream_hourly()     │              │  • Thread-based polling │  │
│  │  • yfinance integration│              │  • Message forwarding   │  │
│  └─────┬──────────────────┘              └───────────┬─────────────┘  │
│        │                                             │                │
└────────┼─────────────────────────────────────────────┼────────────────┘
         │                                             │
         │ yfinance API calls                          │ Kafka topics
         ▼                                             ▼
┌──────────────────┐                          ┌─────────────────────┐
│  Yahoo Finance   │                          │   Apache Kafka      │
│  Market Data API │                          │   Message Broker    │
└──────────────────┘                          └─────────────────────┘
```

---

## Hybrid Architecture Design

Python's concurrency constraints are addressed by separating sync and async into distinct execution contexts.

### Three Execution Contexts

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXECUTION CONTEXT SEPARATION                      │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Thread 1: StreamingService (Background Daemon)              │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  while running:                                              │  │
│  │    for ticker in tickers:                                    │  │
│  │      data = yfinance.Ticker(ticker).history()  # BLOCKS     │  │
│  │      kafka_producer.send(data)                 # BLOCKS     │  │
│  │      update_cache_only(ticker, data)          # No broadcast│  │
│  │    time.sleep(1)                                             │  │
│  │                                                               │  │
│  │  Pure synchronous Python - no async, no event loop           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Thread 2: KafkaWebSocketBridge (Background Daemon)          │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  while not stopped:                                          │  │
│  │    messages = kafka_consumer.poll(timeout=1000)  # BLOCKS   │  │
│  │    for msg in messages:                                      │  │
│  │      data = json.loads(msg.value)                            │  │
│  │      # Bridge to async world:                                │  │
│  │      asyncio.run_coroutine_threadsafe(                       │  │
│  │        update_cache_and_broadcast(data),                     │  │
│  │        main_event_loop                                       │  │
│  │      )                                                        │  │
│  │                                                               │  │
│  │  Pure synchronous Python - Kafka consumer requirement        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Main Thread: FastAPI AsyncIO Event Loop                     │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  async def websocket_endpoint(websocket):                    │  │
│  │    await manager.connect(websocket)                          │  │
│  │    while True:                                               │  │
│  │      data = await websocket.receive_text()                   │  │
│  │      # Handle pings, etc.                                    │  │
│  │                                                               │  │
│  │  async def broadcast(payload):                               │  │
│  │    for connection in active_connections:                     │  │
│  │      await connection.send_json(payload)  # Non-blocking!    │  │
│  │                                                               │  │
│  │  Pure asynchronous Python - cooperative multitasking         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Communication between contexts: asyncio.run_coroutine_threadsafe() │
│  No shared mutable state - event loop provides synchronization     │
└─────────────────────────────────────────────────────────────────────┘
```

### Why This Works

**Fault Isolation**: StreamingService crashes don't affect WebSocket connections. Malformed client data doesn't crash the polling thread. Each context fails independently.

**Zero Coordination**: The streaming thread doesn't know about WebSockets. The Kafka consumer doesn't know about yfinance. The event loop doesn't know about threads. Each does one thing well.

**Independent Optimization**: Each context can be tuned separately—retry logic in threads, connection pooling in async, batch sizes in Kafka—without cross-cutting concerns.

---

## Why Kafka

Kafka is the durable message bus decoupling producers from consumers with ordering guarantees and horizontal scaling.

**Durability & Replay**: Kafka persists messages to disk before acknowledging. Clients reconnect and replay from their last offset—no data loss during network drops. Redis Pub/Sub can't replay (fire-and-forget), RabbitMQ deletes after consumption.

**Ordering Guarantees**: Ticker symbols as message keys route to the same partition via hashing. Kafka guarantees in-partition order. `EURUSD=X` updates always arrive chronologically, preventing chart corruption.

**Horizontal Scaling**: Consumer groups auto-distribute partitions. 16 partitions + 4 consumers = 4 partitions each. Need 10K WebSocket connections? Deploy 10 instances. Kafka rebalances automatically when instances crash or join.

**Multi-Consumer Fan-Out**: Add new consumer groups without touching producer code. Today: WebSocket broadcasting. Tomorrow: TimeSeries DB writer, ML pipeline, audit logger. Each consumes independently, maintaining its own offsets.

The StreamingService continues polling Yahoo Finance once per second per ticker, publishing each update once to Kafka. But three different systems consume each message for three different purposes, with zero additional API calls, zero producer code changes, and zero coordination overhead. This is Kafka's superpower: turning one stream into many streams through independent consumption.

### Data Flow Summary

Market data is polled by the StreamingService (typically at one-minute candle frequency) which first checks whether the latest candle differs from the last published value; identical candles are skipped to avoid unnecessary traffic. When a new value is detected, it is published to a Kafka topic whose key is the ticker symbol, ensuring deterministic partition routing and in-partition ordering. Kafka persists the message and replicates it according to cluster configuration, making the update durable and available to any number of consumers. Consumer adapters subscribe to the topic, hand the message to stream utilities that update the partitioned in-memory cache, and schedule an asynchronous broadcast on the event loop to deliver the JSON payload to connected WebSocket clients. The frontend receives the JSON, updates component state, and re-renders charts; typical end-to-end latency is in the ~200–500ms range. Kafka's role is to decouple the ingestion path from consumers, allowing the same published update to be used by multiple downstream services without extra API calls or producer changes.

---

## Core Components Explained

Each component in our streaming architecture has been carefully designed to solve specific challenges while maintaining clean separation of concerns. Let's examine these components in depth, understanding not just what they do, but why they're designed the way they are and how they interact to create a cohesive system.

### 1. ConnectionManager

Manages WebSocket connection lifecycle: handshake, active messaging, disconnection.

```python
# services/conn_management.py
from fastapi.websockets import WebSocket
from typing import Set, Dict, Any

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Connection failed, mark for removal
                disconnected.add(connection)
        
        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn)
```

- **Set-based storage**: O(1) add/remove for `active_connections`
- **Graceful error handling**: Dead connections removed during broadcast without blocking healthy clients
- **Async-first**: All methods are `async def`, cooperative multitasking via FastAPI ASGI

---

### 2. Stream Utilities

Lightweight utilities manage the in-memory partitioned cache and coordinate broadcasts. The utilities expose concise operations to update cache entries and schedule async broadcasts (e.g., via an event-loop scheduler). Implementation details (workers/threads + run_coroutine_threadsafe) are intentionally kept minimal here—treated as infrastructure glue rather than primary design focus.

---

### 3. Streaming Service

The StreamingService polls market-data APIs, applies fast deduplication (timestamp+close), and publishes only new updates to Kafka topics keyed by ticker. Blocking I/O is isolated from the async runtime (via workers); the service's responsibilities are fetching, deduplicating, and producing.

---

### 4. Kafka Consumers & Bridge

Consumers subscribe to `instant_{ticker}` topics and hand messages to the stream utilities which update cache and trigger async broadcasts. The Kafka bridge is simply a consumer adapter — its implementation may use a worker to isolate blocking Kafka client calls, but that detail is not central to the architecture description.

---

## Streaming Modes

The streaming subsystem can be configured to operate in different modes via the `WS_UPDATES_MODE` environment variable to match deployment constraints. In `auto` mode the service will attempt to connect to Kafka at startup and will fall back to direct WebSocket broadcasting if Kafka is not reachable; this mode is convenient for development and hybrid environments because it preserves service availability when the broker is temporarily unavailable. In `direct` mode the StreamingService bypasses Kafka entirely and calls the cache-and-broadcast path directly; this minimizes latency and is suitable for single-instance deployments or local testing. In `kafka` mode Kafka is required: the service enforces broker availability at startup and refuses to run without it, which is appropriate for production clusters that rely on Kafka for durability, replay, and multi-consumer fan-out. Mode selection is controlled by a small environment-check function in the code that either starts the Kafka bridge or falls back to the direct path depending on configured mode and runtime broker availability.

---

## WebSocket Communication

WebSocket protocol provides persistent bidirectional communication for real-time price updates.

### Frontend WebSocket Client

```typescript
// ui/forex-dash/src/websocket.ts
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private listeners: Set<(data: any) => void> = new Set();
  private pingTimer: number | null = null;
  private shouldReconnect: boolean = true;

  connect() {
    const ws = new WebSocket('ws://localhost:8000/stream/ws');
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      // Send periodic ping to keep connection alive
      this.pingTimer = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      if (event.data === 'pong') return;
      
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'price_update') {
          // Notify all subscribers
          this.listeners.forEach(callback => callback(message));
        }
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(), 3000);
      }
    };

    this.ws = ws;
  }

  subscribe(callback: (data: any) => void) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }
}

export const wsClient = new WebSocketClient();
```

### Message Format

All WebSocket messages follow this structure:

```typescript
interface PriceUpdate {
  type: "price_update";
  ticker: string;              // "EURUSD=X"
  partition: string;           // "1d_1m"
  data: {
    timestamp: string;         // ISO 8601 format
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    period: string;            // "1d"
    interval: string;          // "1m"
  };
}
```

**Example Message:**
```json
{
  "type": "price_update",
  "ticker": "EURUSD=X",
  "partition": "1d_1m",
  "data": {
    "timestamp": "2026-01-16T14:32:00+00:00",
    "open": 1.08234,
    "high": 1.08256,
    "low": 1.08221,
    "close": 1.08245,
    "volume": 1234,
    "period": "1d",
    "interval": "1m"
  }
}
```

---

## Performance Optimizations

### 1. Partitioned Cache

```python
latest_data_cache = {
    "EURUSD=X": {
        "1d_1m": {...},      # 1-day period, 1-minute interval
        "5d_5m": {...},      # 5-day period, 5-minute interval
        "1mo_1d": {...}      # 1-month period, daily interval
    }
}
```

Multiple chart intervals coexist without conflicts, O(1) lookup, minimal memory footprint.

### 2. Inference Caching

ML inference (200-500ms CPU, 50-100ms GPU) is expensive. Cache predictions by ticker+date, expire at UTC midnight.

```python
# Backend cache
inference_cache: Dict[str, Dict[str, Any]] = {}

def get_cached_inference(ticker: str):
    if ticker not in inference_cache:
        return None
    
    cached = inference_cache[ticker]
    today = datetime.utcnow().date().isoformat()
    
    if cached.get("date") == today:
        return cached["result"]
    
    del inference_cache[ticker]  # Expired
    return None
```

```typescript
// Frontend cache
const inferenceCache = new Map<string, InferenceCache>();

const getCachedInference = (ticker: string): InferenceData | null => {
  const cached = inferenceCache.get(ticker);
  if (!cached) return null;
  
  const today = new Date().toISOString().slice(0, 10);
  if (cached.date === today) {
    return cached.data;
  }
  
  inferenceCache.delete(ticker);
  return null;
};
```

**Impact:** Reduces inference API calls by **~99%** (1 call per ticker per day vs. every chart render)

### 3. Connection Pooling

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
```

Using a `Set` instead of a `List` provides substantial performance and reliability advantages for connection management. The set data structure delivers O(1) time complexity for both adding and removing connections, dramatically outperforming the O(n) linear time required by lists. This becomes increasingly important as the number of concurrent connections grows into the hundreds or thousands. Sets also provide automatic deduplication, ensuring that even if connection logic attempts to register the same WebSocket twice, only one instance exists in the collection. When combined with proper locking mechanisms, sets offer thread-safe operations that allow multiple threads to safely read from and write to the connection pool without risking data corruption or race conditions.

---

## Complete Request Flow Example

### Step 1: User Starts Streaming
```http
POST http://localhost:8000/stream/start_instant_streaming
```

### Step 2: Backend Response
```json
{
  "message": "Instant streaming started",
  "tickers": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", ...]
}
```

### Step 3: Background Thread Starts Polling
```python
# Every 1 second
ticker_obj = yf.Ticker("EURUSD=X")
data = ticker_obj.history(period="1d", interval="1m")
latest_candle = data.iloc[-1]
```

### Step 4: Data Processing
```python
message = {
    "ticker": "EURUSD=X",
    "timestamp": "2026-01-16T14:32:00+00:00",
    "close": 1.08245,
    # ... other OHLCV data
}

# Update cache
latest_data_cache["EURUSD=X"]["1d_1m"] = message

# Broadcast to WebSocket clients
asyncio.run_coroutine_threadsafe(
    manager.broadcast(payload),
    ws_broadcast_loop
)
```

Last-mile summary: consumed Kafka messages are scheduled to the async broadcaster, which sends JSON updates to connected clients; the frontend receives the JSON, updates component state, and redraws charts. Typical end-to-end latency from market-data fetch to chart update is in the ~200–500ms range.

---

## Monitoring and Debugging

### Backend Logs
```
[WebSocket] Client connected, total connections: 1
[WebSocket] Event loop set: True
[INSTANT STREAMING] Started for 10 tickers
[WebSocket] Broadcasted update for EURUSD=X: 1.08245
[WebSocket] Broadcasted update for GBPUSD=X: 1.26534
```

### Frontend Console
```
WebSocket connected
Received price update: EURUSD=X @ 1.08245
Chart updated with 347 points
```

### Kafka Monitoring
```bash
# List topics
kafka-topics --list --bootstrap-server localhost:9092

# Monitor instant topic
kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic instant_eurusdx \
  --from-beginning
```

---

## Deployment Considerations

Taking a streaming system from localhost development to production deployment introduces a new dimension of complexity. What works perfectly on a single developer's machine can fail spectacularly when exposed to real-world network conditions, multiple concurrent users, container orchestration, and production security requirements. These considerations must inform architectural decisions from the beginning, not be retrofitted later as afterthoughts.

### Containerization Strategy

The deployment model leverages Docker containers to encapsulate the entire application stack. The FastAPI backend, including all streaming logic, runs in one container. The React frontend builds into static files served by nginx in another container. ML model files are baked into the container image at build time, ensuring version consistency between development and production. This containerization provides several critical benefits:

First, environment reproducibility. The exact Python version, library versions, and system dependencies that worked in development are guaranteed present in production. This eliminates the notorious "works on my machine" problem that plagues applications with complex dependency trees. If yfinance 0.2.28 works during development, the Dockerfile pins that exact version, preventing surprise breakage from automatic upgrades.

Second, resource isolation. Each container has defined CPU and memory limits, preventing a runaway polling thread or memory leak from consuming all available resources and crashing the host system. Kubernetes or Docker Compose enforce these limits at the orchestration layer, killing containers that exceed thresholds before they can impact other services.

Third, deployment atomicity. A new version of the streaming service can be built into a fresh container image, tested in staging, then promoted to production by simply updating the image tag. Rollback is equally simple—revert to the previous image tag. This beats manual server updates, file copying, and process restarts by an enormous margin in both reliability and speed.

### Scaling Considerations

A single FastAPI backend instance can comfortably handle 50-100 concurrent WebSocket connections before resource constraints emerge. For higher scale, horizontal scaling becomes necessary, but introduces new challenges for a stateful streaming system. The core problem: WebSocket connections are stateful, pinned to a specific backend instance. If a client connects to Instance A, broadcasts from Instance B won't reach that client unless we implement inter-instance message routing.

The Kafka integration provides an elegant solution to this scaling challenge. Instead of each backend instance polling yfinance independently (wasteful and risks rate limiting), a single dedicated instance acts as the data producer, fetching market data and publishing to Kafka topics. All other backend instances subscribe as Kafka consumers, receiving the same stream of market data. Each instance then broadcasts to its own connected WebSocket clients. This pub-sub architecture allows linear scaling: need to support 500 concurrent users? Deploy 10 backend instances, each handling 50 connections.

An alternative approach for environments without Kafka uses sticky sessions at the load balancer layer. Nginx or HAProxy can pin each client to a specific backend instance based on IP address or session cookie. While simpler than Kafka, this approach has drawbacks: uneven load distribution when some clients are more active than others, and session loss during backend instance restarts forcing client reconnection.

### Security Hardening

Production deployment demands security measures absent in development environments. WebSocket connections must occur over WSS (WebSocket Secure), the encrypted equivalent of HTTPS. This requires TLS certificates provisioned through Let's Encrypt or a certificate authority, configured at the reverse proxy layer in front of the FastAPI application. Unencrypted WS connections expose market data and potentially user authentication credentials to network sniffing attacks.

Authentication and authorization represent another critical layer. The current implementation assumes trusted network access, but production systems should implement token-based authentication. Each WebSocket connection handshake should include an authentication token validated against a user database or JWT signing key. This prevents unauthorized users from connecting and consuming valuable backend resources.

Rate limiting protects against both malicious attacks and accidental resource exhaustion. Backend endpoints should enforce limits on requests per IP address or user account: perhaps 100 API requests per minute and 5 concurrent WebSocket connections per user. Clients exceeding these limits receive 429 Too Many Requests responses. This prevents a single misbehaving or malicious client from monopolizing backend resources.

### Operational Excellence

Running streaming systems in production requires ongoing operational discipline. Health check endpoints enable Kubernetes or load balancers to detect unhealthy backend instances and stop routing traffic to them. The `/health` endpoint verifies not just that the HTTP server is responding, but that critical dependencies like Kafka (if enabled) are reachable and that the streaming thread is actively running.

Graceful shutdown handling ensures in-flight requests complete before the server terminates. When receiving a SIGTERM signal (Kubernetes pod termination), the FastAPI application should stop accepting new connections, wait for existing WebSocket clients to be notified and disconnect cleanly, flush any buffered logs or metrics, then exit. This prevents abrupt connection drops that appear as errors to end users.

Configuration management through environment variables allows the same container image to be deployed across development, staging, and production environments with different settings. Kafka broker addresses, yfinance API keys, CORS allowed origins, log verbosity—all these should be configurable externally without rebuilding the image. This supports the Twelve-Factor App methodology and simplifies deployment pipelines.

---

## Conclusion

This architecture combines async WebSocket broadcasting with Kafka-based message passing and lightweight workers to keep blocking I/O off the main event loop. Kafka provides durable, partitioned topics for replay and fan-out; the frontend receives JSON updates and re-renders charts with low latency.

Key takeaways: clear separation of concerns (fetch → produce → consume → broadcast), efficient deduplication, and a small set of operational knobs (mode selection, retention, replication) that make the system production-ready and easy to scale.
