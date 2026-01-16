Real-Time Forex Streaming: Architecture, MLOps Pipeline, Data Stream, and ETL

This expanded document ties the repository implementation to a production-minded operational model. It describes how data flows from external market sources into Kafka, how the streaming and batch pipelines are organized, the MLOps lifecycle for models, and practical optimizations and configuration suggestions tailored to this codebase.

Architecture summary

The project is organized around a small async core that serves WebSocket clients and a set of blocking workers that perform polling, Kafka interactions, and heavy computation. Producers (implemented in `api/services/streaming_service.py`) poll `yfinance` for multiple resolutions, deduplicate repeated candles, and publish messages to partitioned Kafka topics via `api/services/kafka_service.py`. A background bridge (`api/services/kafka_bridge.py`) consumes Kafka and forwards messages into `api/services/utils/stream_utils.py`, which updates a partitioned in-memory cache and schedules broadcasts using the `ConnectionManager` in `api/services/conn_management.py`.

Execution contexts and responsibilities

- Producers: Dedicated processes or containers run the streaming service at configurable intervals (instant, hourly, daily). They are purely synchronous and isolate blocking HTTP calls and producer logic.
- Broker: Kafka acts as the durable, partitioned message bus. Topics are keyed by ticker to guarantee in-partition ordering and replayability.
- Bridge/consumer: A synchronous consumer runs in a background thread; it deserializes messages and invokes a handler that performs cache updates and schedules async broadcasts.
- Async core: The FastAPI-based async service manages WebSocket lifecycle, accepts client subscriptions, and performs non-blocking broadcasts. Heavy CPU-bound work (e.g., ONNX inference) is delegated to worker pools or separate inference services.

Data stream and ETL pipeline

1) Data acquisition: The system primarily uses `yfinance` to fetch historical and near-real-time data. `StreamingService` supports multiple modes: "instant" (1m/2m and tick updates), hourly, and daily. It builds canonical candles, performs timestamp/close deduplication, and emits a compact JSON payload.

2) Produce and partition: Messages are produced to Kafka topics named by resolution and ticker (for example, `instant_eurusd`). The `KafkaService` ensures topics exist and enforces a topic partition count; the producer applies a CRC32-based partitioning on the ticker key for deterministic routing.

3) Consumption and materialization: Consumers (bridge or service consumers) read messages and update a partitioned `latest_data_cache` keyed as `latest_data_cache[ticker][period_interval]`. The cache contains only the latest candle per partition to keep memory bounded. A separate Redis-backed `CacheService` stores short-lived key/value entries for cross-instance coordination or lookups.

4) Feature engineering: The `FeatureStore` reconstructs recent history by consuming from Kafka topics to produce windowed historical series. It computes lag features, log returns, rolling stats, and other engineered features on demand for inference and training.

5) Inference and model artifacts: Models are exported as ONNX in `inference_models/` along with scalers and metadata. `InferenceService` caches loaded artifacts to avoid repeated disk I/O. For production-grade serving, inference should run in a separate process or GPU-backed service to prevent blocking the async broadcaster.

MLOps pipeline and lifecycle

Training and tuning: Offline model training uses notebooks and scripts in `Notebooks/` with hyperparameter search orchestrated by Ray Tune. Experiments are logged to MLflow under `mlruns/` with artifacts saved to `inference_models/` for deployment.

Model registry and promotion: After tuning and validation, model artifacts are versioned and promoted (the repo uses MLflow as the experiment and artifact store). The deployment process should reference model versions or artifact hashes for reproducibility.

Deployment and serving: Serving is provided via FastAPI and the streaming pathway. There are two complementary serving patterns in this repo: (a) real-time streaming (Kafka → bridge → WebSocket) for live charting and (b) REST inference endpoints that accept feature payloads for ad-hoc predictions. Containerization via `docker-compose.yml` is provided for local stacks; production rollout should use orchestrators (Kubernetes) with rolling updates and readiness probes.

CI/CD and reproducibility: The repo includes GitHub Actions CI and Docker containers. Recommended continuous steps: test suite, static analysis (lint/format), training and smoke test of model exports, and a staged deployment to a test environment where Kafka and the async backend are available.

Technology stack (as used in repository)

- Python (3.9+): core language
- FastAPI / Uvicorn: async web server and WebSocket API
- kafka-python: Kafka clients (`KafkaProducer`, `KafkaConsumer`, `KafkaAdminClient`)
- yfinance / pandas / numpy: data acquisition and ETL
- Ray Tune: hyperparameter search and tuning
- MLflow: experiment tracking and artifact registry
- ONNX Runtime: portable model serving
- Redis: optional cross-instance caching and TTL storage
- Prometheus / Grafana: metrics and dashboards
- Docker / docker-compose: local development and reproducible images

Concrete optimizations and configuration guidance

- Producer tuning: set `linger.ms` to a low value (e.g., 5–50ms) for near-real-time updates and a small `batch.size` to cap latency. Use compression (LZ4/Snappy) to reduce broker I/O. Keep `acks='all'` for durability but use limited retries and `max_in_flight_requests_per_connection=1` to preserve ordering.
- Consumer tuning: set `max.poll.records` to a number matching the expected per-message processing time; use `consumer_timeout_ms` cautiously in bridge threads. For heavier per-message work, use an internal queue and a worker pool.
- Broadcast architecture: shard broadcasts into small batches and use `asyncio.gather` with timeouts. Use per-connection queues and drop stale messages for slow clients.
- Serialization: adopt `orjson` for message encoding/decoding hot paths. If binary formats become necessary, consider MessagePack or Avro with a compact schema.
- Resource isolation: run inference in separate processes/containers; pin CPU/GPU resources. Use ulimits and tuned ephemeral port ranges for the FastAPI containers.

Observability and SLOs

Monitor end-to-end latency (produce → consume → broadcast) and set SLOs for median and tail latencies. Collect metrics for message lag, consumer offsets, and broadcast success/failure rates. Centralize logs and add structured logging to background workers for quick triage.

Security and compliance

Terminate TLS at the edge, require authenticated WebSocket handshakes (JWT), and restrict Kafka and Redis access to internal networks. Use role-based access for model artifact promotion and maintain tamper-evident artifacts in the model registry.

Practical next steps (suggested)

1. Add a small docker-compose profile that runs a single-node Kafka, Zookeeper, Redis, and the API for local integration tests and replay harnesses.
2. Add a lightweight replay script that publishes historical candles to Kafka for perf testing the consumer→broadcast loop.
3. Add health checks that validate the streaming thread, Kafka connectivity, and Redis reachability.

If you want, I can implement any of the next steps: the local docker-compose profile, the replay harness, or sequence diagrams for the most critical flows.
