Title: Building a production-ready ETL for forex time-series with yfinance, S3, Spark, Airflow and Postgres
----

Summary
-------

This article describes a practical, production-focused ETL that: fetches forex time-series with `yfinance`, stages raw CSVs to AWS S3, transforms and enriches them with a PySpark job, writes partitioned Parquet back to S3, and loads the cleaned data into Postgres (or Redshift) — all orchestrated by Airflow with validation and monitoring.

Why this design
-----------------

- yfinance: lightweight, reliable source for historical forex/stock data during prototyping and production ingestion.
- S3: durable object storage for raw and processed data; serves as the single source-of-truth and enables cost-efficient querying (Parquet + Glue/Athena).
- Spark: scalable data processing for cleaning and feature engineering; plays well with parquet and partitioning.
- Airflow: orchestration, scheduling, retries, observability and easy integration with Spark or EMR.
- Postgres/Redshift: final analytical store; Postgres for small/medium workloads and Redshift (COPY from S3) for large-scale analytics.

Repository map (key files)
--------------------------

- `etl/extract/yfinance_s3.py` — fetcher that downloads data via `yfinance` and uploads raw CSV to S3.
- `etl/transform/spark_transform.py` — PySpark job to read raw CSVs from S3, normalize schema and write partitioned Parquet to S3.
- `etl/airflow/dags/forex_yfinance_etl.py` — Airflow DAG orchestrating the fetch → spark → load → validate flow.
- `etl/load/load_to_sql.py` — loader with an idempotent upsert implementation for Postgres (staging + INSERT ... ON CONFLICT).
- `etl/utils/validation.py` — validation helpers (counts, null checks, continuity) plus SNS alerting.
- `.env` — environment variables used by the DAG locally. (In production you should use Airflow Connections/Secrets Manager.)

High-level flow
---------------

1. Airflow triggers DAG per schedule.
2. PythonOperator runs `fetch_and_upload()` to download new data for configured tickers and upload raw CSV to `s3://bucket/forex/raw/...`; the task returns the S3 path via XCom.
3. SparkSubmitOperator launches `spark_transform.py` with `--input` set to the uploaded S3 object (s3a://) and `--output` set to `s3a://bucket/forex/processed/{{ ds }}`. The job reads CSV, normalizes columns, casts types and writes Parquet partitioned by `ticker` and `date`.
4. A PythonOperator runs the loader `load_parquet_to_postgres_upsert()` to read the processed Parquet (via `pyarrow` + `s3fs`) into a staging table and performs an upsert into the target Postgres table using `INSERT ... ON CONFLICT`.
5. Validation step runs `run_full_validation()` which counts rows (raw vs processed vs DB), runs null checks, and continuity checks. On failure it publishes an SNS alert.

Why upsert and staging
-----------------------

Direct row-by-row upserts via JDBC are slow and non-idempotent. The chosen pattern:

- write incoming data into a temporary/staging table (fast bulk write via pandas/SQLAlchemy or COPY)
- once staging is loaded, run a single SQL `INSERT ... ON CONFLICT` (Postgres) to merge rows into the production table. This guarantees atomicity and idempotency and is suitable for daily batch workloads.

Key implementation notes
------------------------

- S3 connectors: use `s3a://` when running on Spark (EMR/Glue) and `s3://` for Python-based reads (pandas + s3fs). Ensure the Hadoop AWS JARs or EMR Glue runtime provides the correct S3 connector.
- Credentials & security: never hard-code AWS credentials. Use IAM Roles for EMR/Glue/EC2 and Airflow connections or AWS Secrets Manager for DB credentials.
- Partitioning: processed Parquet is written partitioned by `ticker` and `date` to speed downstream queries and make incremental processing straightforward.
- Parquet: columnar storage reduces storage & compute costs for analytical queries. Use Snappy compression by default (Spark will pick an efficient codec).

How to run locally (dev)
------------------------

1. Create and activate a virtualenv, then install Python deps (see `api/requirements.txt`):

```powershell
.venv\Scripts\Activate.ps1
pip install -r api/requirements.txt
```

2. Populate `.env` with your local/dev settings (S3 bucket, DB URI). For real deployments prefer Airflow Variables/Connections.

3. Run fetch script manually (example):

```powershell
python -m etl.extract.yfinance_s3 EURUSD=X --start 2024-01-01 --end 2025-01-01 --bucket my-bucket --prefix forex
```

4. Run the Spark job locally with `spark-submit` (ensure Hadoop AWS jars on classpath if using S3):

```bash
spark-submit etl/transform/spark_transform.py --input s3a://my-bucket/forex/raw/... --output s3a://my-bucket/forex/processed/2025-01-01/
```

5. Or let Airflow orchestrate everything: put the DAG under your Airflow `dags/` folder and start scheduler/webserver:

```bash
airflow db init
airflow webserver --port 8080
airflow scheduler
# then enable the DAG from UI or CLI
airflow dags unpause forex_yfinance_etl
airflow dags trigger forex_yfinance_etl
```

Testing strategy
----------------

- Unit tests: mock `yfinance` and `boto3` to validate `fetch_and_upload()` behavior. See `tests/test_yfinance_s3.py` in the repo.
- Integration test for upsert: a local test uses SQLite (or ephemeral Postgres) to validate the staging + upsert behavior. See `tests/test_load_upsert_sqlite.py`.
- End-to-end integration: run the DAG in a dev Airflow instance pointing to a test S3 bucket and a test Postgres to verify the complete flow.

Monitoring & alerting
---------------------

- Airflow alerts: configure email/Slack/SNS alerts in Airflow for DAG failures and task retries.
- Validation alerts: the DAG calls `run_full_validation()` after loading; if any check fails the function publishes to an SNS topic (configurable via Airflow Variable `SNS_TOPIC_ARN`).
- Metrics: push counts (raw, processed, db) to your metrics system (Prometheus/CloudWatch) from within the validation step for long-term monitoring.

Production considerations and optimizations
-----------------------------------------

- Redshift: for large-scale loads prefer generating a manifest and using Redshift `COPY` from S3 with an IAM role — much faster than JDBC bulk inserts.
- Glue Catalog: register the processed Parquet with Glue Catalog so Athena/Redshift Spectrum can query it without loading into the DB.
- Partition retention: set S3 lifecycle policies to move raw/old data to cheaper storage classes (GLACIER) as needed.
- Concurrency & idempotency: keep the pipeline idempotent by enforcing unique keys (`ticker`,`date`), and use DAG run date templating when writing processed output (we do this today with `{{ ds }}`).

Files to look at in this repo
----------------------------

- [etl/extract/yfinance_s3.py](etl/extract/yfinance_s3.py) — fetch + S3 upload
- [etl/transform/spark_transform.py](etl/transform/spark_transform.py) — PySpark transform job
- [etl/airflow/dags/forex_yfinance_etl.py](etl/airflow/dags/forex_yfinance_etl.py) — DAG wiring and XCom usage
- [etl/load/load_to_sql.py](etl/load/load_to_sql.py) — upsert loader (staging + ON CONFLICT)
- [etl/utils/validation.py](etl/utils/validation.py) — validation and SNS alerting
- [.env](.env) — template environment variables used by the DAG locally

Conclusion
----------

This repo includes a working reference ETL for forex time-series using `yfinance` + S3 + Spark + Airflow + Postgres. It balances prototyping speed with production-grade considerations: idempotency, validation, monitoring, and scale-friendly patterns (S3+Parquet, Spark). Use the documented files and tests as a starting point — swap Postgres for Redshift in the loader for bigger workloads, and move secrets into Airflow Connections/Secrets Manager before production deployment.
