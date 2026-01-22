**Airflow Quickstart**

- **Purpose:** Automate creation of Airflow Variables and Connections needed by the `forex_yfinance_etl` DAG.
- **Files:** `scripts/setup_airflow_env.ps1` (PowerShell), `scripts/setup_airflow_env.sh` (Bash).

Pre-requisites
-------------

- Airflow CLI installed and available in PATH (same environment that runs the Airflow scheduler/webserver).
- Your `.env` configured for local dev OR Airflow connections for production secrets.

Usage (PowerShell)
-------------------

Run from repository root in PowerShell (adjust values as needed):

```powershell
.\scripts\setup_airflow_env.ps1 -S3Bucket my-bucket -S3Prefix forex -PgConnId postgres_default -TargetTable public.forex_prices -SnsTopicArn arn:aws:sns:us-east-1:123456789012:my-topic
```

Usage (Bash)
------------

```bash
bash scripts/setup_airflow_env.sh my-bucket forex postgres_default public.forex_prices arn:aws:sns:us-east-1:123456789012:my-topic
```

What the scripts do
--------------------

- Create Airflow Variables: `S3_BUCKET`, `S3_PREFIX`, `PG_CONN_ID`, `TARGET_TABLE`, `SNS_TOPIC_ARN`.
- Add a placeholder Airflow Connection for Postgres (if not present) using the provided `pg_conn_id`.
 - Create Airflow Variables: `S3_BUCKET`, `S3_PREFIX`, `PG_CONN_ID`, `TARGET_TABLE`, `SNS_TOPIC_ARN`.
 - Optional/production variables supported by DAG: `AWS_CONN_ID`, `SPARK_CONN_ID`, `ETL_TICKER`, `ETL_START`, `ETL_END`, `SCHEDULE_INTERVAL`, `MIN_ROWS`, `ALERT_EMAILS`.
 - Add a placeholder Airflow Connection for Postgres (if not present) using the provided `pg_conn_id`.

Security note
-------------

Do not store production credentials in plaintext. Use Airflow Connections with secrets backends (Vault, AWS Secrets Manager) or the environment native secret store.
