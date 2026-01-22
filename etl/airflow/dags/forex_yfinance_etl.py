"""Airflow DAG to orchestrate yfinance -> S3 -> Spark -> SQL -> validation (moved under etl/airflow)."""
from __future__ import annotations

from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from airflow import DAG
from airflow.models import Variable
from airflow.hooks.base import BaseHook
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from etl.extract.yfinance_s3 import fetch_and_upload
from etl.load.load_to_sql import load_parquet_to_postgres
from etl.utils.validation import send_sns_alert


ALERT_EMAILS = Variable.get("ALERT_EMAILS", default_var=os.getenv("ALERT_EMAILS", None))

DEFAULT_ARGS = {
    "owner": "etl",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(hours=1),
    "email": ALERT_EMAILS.split(",") if ALERT_EMAILS else [],
    "email_on_failure": True,
}


def load_sql_callable(**context):
    params = context["params"]
    processed_path = params["processed_path"]
    table = params["table"]
    pg_uri = params["pg_uri"]
    storage_options = params.get("storage_options")
    load_parquet_to_postgres(processed_path, table, pg_uri, storage_options=storage_options)


def validate_callable(**context):
    params = context["params"]
    from etl.utils.validation import run_full_validation, send_sns_alert

    try:
        result = run_full_validation(
            processed_s3_path=params["processed_path"],
            raw_s3_path=params["raw_path"],
            pg_uri=params["pg_uri"],
            table=params["table"],
            storage_options=params.get("storage_options"),
            min_rows=params.get("min_rows", 1),
        )
        context["ti"].xcom_push(key="validation_result", value=result)
    except Exception as exc:
        topic = params.get("sns_topic_arn")
        if topic:
            try:
                send_sns_alert(topic, subject="ETL Validation Failed", message=str(exc))
            except Exception:
                pass
        raise


load_dotenv()


S3_BUCKET = Variable.get("S3_BUCKET", default_var=os.getenv("S3_BUCKET", "my-bucket"))
S3_PREFIX = Variable.get("S3_PREFIX", default_var=os.getenv("S3_PREFIX", "forex"))
PG_CONN_ID = Variable.get("PG_CONN_ID", default_var=os.getenv("PG_CONN_ID", "postgres_default"))
AWS_CONN_ID = Variable.get("AWS_CONN_ID", default_var=os.getenv("AWS_CONN_ID", "aws_default"))
try:
    PG_CONN = BaseHook.get_connection(PG_CONN_ID)
    PG_URI = PG_CONN.get_uri()
except Exception:
    PG_URI = Variable.get("PG_URI", default_var=os.getenv("PG_URI", "postgresql://username:password@hostname:5432/dbname"))

SNS_TOPIC_ARN = Variable.get("SNS_TOPIC_ARN", default_var=os.getenv("SNS_TOPIC_ARN", None))

# build storage_options from AWS connection if possible (allows using Airflow Connections / Secrets backend)
storage_options = None
try:
    aws_conn = BaseHook.get_connection(AWS_CONN_ID)
    extras = getattr(aws_conn, "extra_dejson", {}) or {}
    storage_options = {}
    if aws_conn.login:
        storage_options["aws_access_key_id"] = aws_conn.login
    if aws_conn.password:
        storage_options["aws_secret_access_key"] = aws_conn.password
    # common extra keys
    for k in ("region_name", "aws_session_token", "endpoint_url"):
        if k in extras:
            storage_options[k] = extras[k]
    if not storage_options:
        storage_options = None
except Exception:
    storage_options = None


def _on_failure(context):
    """Global failure handler: send SNS/email if configured."""
    try:
        topic = Variable.get("SNS_TOPIC_ARN", default_var=None)
        if topic:
            msg = f"DAG {context['dag'].dag_id} failed for run {context['ts']}: {context.get('exception')}"
            send_sns_alert(topic, subject=f"Airflow DAG failure: {context['dag'].dag_id}", message=msg)
    except Exception:
        pass


with DAG(
    dag_id="forex_yfinance_etl",
    default_args=DEFAULT_ARGS,
    description="Fetch forex data from yfinance, process with Spark, load to SQL",
    start_date=datetime(2025, 1, 1),
    schedule_interval=Variable.get("SCHEDULE_INTERVAL", default_var=os.getenv("SCHEDULE_INTERVAL", "0 2 * * *")),
    catchup=False,
    on_failure_callback=_on_failure,
) as dag:

    TICKER = Variable.get("ETL_TICKER", default_var=os.getenv("ETL_TICKER", "EURUSD=X"))
    FETCH_START = Variable.get("ETL_START", default_var=os.getenv("ETL_START", "2024-01-01"))
    FETCH_END = Variable.get("ETL_END", default_var=os.getenv("ETL_END", "2025-01-01"))

    fetch = PythonOperator(
        task_id="fetch_and_upload",
        python_callable=fetch_and_upload,
        op_kwargs={
            "ticker": TICKER,
            "start": FETCH_START,
            "end": FETCH_END,
            "bucket": S3_BUCKET,
            "prefix": S3_PREFIX,
            "aws_profile": None,
            "region_name": storage_options.get("region_name") if storage_options else None,
        },
    )

    spark_transform = SparkSubmitOperator(
        task_id="spark_transform",
        application="/opt/airflow/dags/etl/transform/spark_transform.py",
        conn_id=Variable.get("SPARK_CONN_ID", default_var="spark_default"),
        application_args=[
            "--input",
            "{{ ti.xcom_pull(task_ids='fetch_and_upload')['s3a_uri'] }}",
            "--output",
            f"s3a://{S3_BUCKET}/{S3_PREFIX}/processed/{{{{ ds }}}}",
        ],
        conf=(
            {
                "spark.hadoop.fs.s3a.access.key": storage_options.get("aws_access_key_id"),
                "spark.hadoop.fs.s3a.secret.key": storage_options.get("aws_secret_access_key"),
            }
            if storage_options
            else {}
        ),
    )

    load_sql = PythonOperator(
        task_id="load_to_sql",
        python_callable=load_sql_callable,
        provide_context=True,
        params={
            "processed_path": f"s3://{S3_BUCKET}/{S3_PREFIX}/processed/{{{{ ds }}}}/",
            "raw_path": "{{ ti.xcom_pull(task_ids='fetch_and_upload')['s3_uri'] }}",
            "table": Variable.get("TARGET_TABLE", default_var=os.getenv("TARGET_TABLE", "public.forex_prices")),
            "pg_uri": PG_URI,
            "storage_options": storage_options,
            "sns_topic_arn": SNS_TOPIC_ARN,
        },
    )

    validate = PythonOperator(
        task_id="validation",
        python_callable=validate_callable,
        provide_context=True,
        params={
            "table": Variable.get("TARGET_TABLE", default_var=os.getenv("TARGET_TABLE", "public.forex_prices")),
            "pg_uri": PG_URI,
            "min_rows": int(Variable.get("MIN_ROWS", default_var=os.getenv("MIN_ROWS", "1"))),
            "storage_options": storage_options,
            "sns_topic_arn": SNS_TOPIC_ARN,
        },
    )

    fetch >> spark_transform >> load_sql >> validate
