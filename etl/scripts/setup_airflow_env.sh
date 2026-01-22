#!/usr/bin/env bash
set -euo pipefail

S3_BUCKET=${1:-my-bucket}
S3_PREFIX=${2:-forex}
PG_CONN_ID=${3:-postgres_default}
TARGET_TABLE=${4:-public.forex_prices}
SNS_TOPIC_ARN=${5:-}
AWS_CONN_ID=${6:-aws_default}
SPARK_CONN_ID=${7:-spark_default}
ETL_TICKER=${8:-EURUSD=X}
ALERT_EMAILS=${9:-}

echo "Setting Airflow Variables..."
airflow variables set S3_BUCKET "$S3_BUCKET"
airflow variables set S3_PREFIX "$S3_PREFIX"
airflow variables set PG_CONN_ID "$PG_CONN_ID"
airflow variables set TARGET_TABLE "$TARGET_TABLE"
airflow variables set AWS_CONN_ID "$AWS_CONN_ID"
airflow variables set SPARK_CONN_ID "$SPARK_CONN_ID"
airflow variables set ETL_TICKER "$ETL_TICKER"
if [[ -n "$ALERT_EMAILS" ]]; then
  airflow variables set ALERT_EMAILS "$ALERT_EMAILS"
fi
if [[ -n "$SNS_TOPIC_ARN" ]]; then
  airflow variables set SNS_TOPIC_ARN "$SNS_TOPIC_ARN"
fi

echo "Ensuring Postgres connection exists (placeholder)..."
if ! airflow connections get "$PG_CONN_ID" >/dev/null 2>&1; then
  echo "Creating placeholder Postgres connection ($PG_CONN_ID). Update credentials in Airflow UI or via CLI."
  airflow connections add "$PG_CONN_ID" --conn-uri "postgresql://user:password@hostname:5432/dbname"
else
  echo "Connection $PG_CONN_ID already exists."
fi

echo "Done."
