# ETL: yfinance → S3 → Spark → Airflow → Postgres

This folder contains the ETL implementation for fetching forex time-series data from Yahoo Finance, transforming it with PySpark, and loading it into a SQL database.

Structure
---------

- `etl/extract/` — data extraction scripts (yfinance fetch + S3 upload)
- `etl/transform/` — PySpark transformation jobs
- `etl/load/` — loaders for Postgres/Redshift (upsert implementations)
- `etl/utils/` — validation and monitoring helpers
- `etl/airflow/dags/` — Airflow DAGs that orchestrate the ETL
- `etl/docs/` — ETL-specific documentation and quickstart

See `etl/docs/etl_yfinance_s3_spark_airflow_postgres.md` for a full article-style walkthrough and `etl/docs/quickstart_airflow.md` for Airflow setup helpers.
