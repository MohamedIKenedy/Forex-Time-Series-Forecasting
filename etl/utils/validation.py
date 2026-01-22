"""Validation and monitoring helpers for the ETL (moved from api/services)."""
from __future__ import annotations

from typing import Optional

import boto3
import pandas as pd
import s3fs
import pyarrow.parquet as pq
from sqlalchemy import create_engine, text


def row_count(table: str, pg_uri: str) -> int:
    engine = create_engine(pg_uri)
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        return int(result.scalar() or 0)


def count_parquet_rows(s3_path: str, storage_options: Optional[dict] = None) -> int:
    storage_options = storage_options or {}
    fs = s3fs.S3FileSystem(**storage_options)
    pattern = s3_path.rstrip("/") + "/**/*.parquet"
    files = fs.glob(pattern)
    total = 0
    for f in files:
        with fs.open(f, "rb") as fh:
            pf = pq.ParquetFile(fh)
            total += pf.metadata.num_rows
    return total


def count_csv_rows(s3_path: str, storage_options: Optional[dict] = None, chunksize: int = 100_000) -> int:
    storage_options = storage_options or {}
    fs = s3fs.S3FileSystem(**storage_options)
    pattern = s3_path.rstrip("/") + "/**/*.csv"
    files = fs.glob(pattern)
    total = 0
    for f in files:
        with fs.open(f, "rb") as fh:
            for chunk in pd.read_csv(fh, chunksize=chunksize):
                total += len(chunk)
    return total


def null_checks_sql(table: str, pg_uri: str, columns: list[str]) -> bool:
    engine = create_engine(pg_uri)
    with engine.connect() as conn:
        for col in columns:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL"))
            cnt = int(result.scalar() or 0)
            if cnt > 0:
                raise AssertionError(f"Null check failed: {col} has {cnt} nulls")
    return True


def continuity_check(table: str, pg_uri: str, date_col: str = "date", ticker_col: str = "ticker", max_gap_days: int = 2) -> bool:
    engine = create_engine(pg_uri)
    sql = f"""
    WITH ranked AS (
      SELECT {ticker_col}, {date_col}::date as d,
             LAG({date_col}::date) OVER (PARTITION BY {ticker_col} ORDER BY {date_col}::date) as prev_d
      FROM {table}
    )
    SELECT COUNT(*) FROM ranked WHERE prev_d IS NOT NULL AND (d - prev_d) > {max_gap_days}
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        gaps = int(result.scalar() or 0)
        if gaps > 0:
            raise AssertionError(f"Continuity check failed: found {gaps} gaps larger than {max_gap_days} days")
    return True


def run_full_validation(
    processed_s3_path: str,
    raw_s3_path: str,
    pg_uri: str,
    table: str,
    storage_options: Optional[dict] = None,
    min_rows: int = 1,
) -> dict:
    storage_options = storage_options or {}
    processed_count = count_parquet_rows(processed_s3_path, storage_options=storage_options)
    raw_count = count_csv_rows(raw_s3_path, storage_options=storage_options)
    db_count = row_count(table, pg_uri)

    if processed_count < min_rows:
        raise AssertionError(f"Processed rows {processed_count} < min_rows {min_rows}")
    if processed_count > raw_count:
        raise AssertionError(f"Processed ({processed_count}) > raw ({raw_count}) — unexpected")
    if db_count < processed_count:
        raise AssertionError(f"DB rows ({db_count}) < processed rows ({processed_count}) — load may have failed")

    null_checks_sql(table, pg_uri, ["ticker", "date", "close"])
    continuity_check(table, pg_uri)

    return {"raw_count": raw_count, "processed_count": processed_count, "db_count": db_count}


def send_sns_alert(topic_arn: str, subject: str, message: str, aws_profile: Optional[str] = None, region_name: Optional[str] = None) -> None:
    session = boto3.Session(profile_name=aws_profile, region_name=region_name) if aws_profile else boto3.Session(region_name=region_name)
    sns = session.client("sns")
    sns.publish(TopicArn=topic_arn, Subject=subject, Message=message)
