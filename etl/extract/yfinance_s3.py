"""Fetch forex series with yfinance and upload CSV to S3.

Functions:
- fetch_and_upload: download ticker data and upload CSV to S3
"""
from __future__ import annotations

from io import StringIO
from datetime import date
from typing import Optional

import yfinance as yf
import boto3
import pandas as pd


def _make_s3_key(prefix: str, ticker: str, ingest_date: Optional[date] = None) -> str:
    ingest_date = ingest_date or date.today()
    return f"{prefix}/raw/{ticker}/ingest_date={ingest_date.isoformat()}/{ticker}_{ingest_date.isoformat()}.csv"


def fetch_and_upload(
    ticker: str,
    start: str,
    end: str,
    bucket: str,
    prefix: str,
    aws_profile: Optional[str] = None,
    region_name: Optional[str] = None,
) -> str:
    """Download historical data for `ticker` using yfinance and upload CSV to S3.

    Returns the S3 key uploaded.

    Arguments:
        ticker: ticker symbol supported by yfinance (e.g. 'EURUSD=X')
        start: start date string 'YYYY-MM-DD'
        end: end date string 'YYYY-MM-DD'
        bucket: target S3 bucket name
        prefix: prefix inside bucket (e.g. 'forex')
        aws_profile: optional boto3 profile name
        region_name: optional region for boto3 client
    """
    # Download
    df = yf.download(ticker, start=start, end=end, progress=False)
    if df is None or df.empty:
        raise ValueError(f"No data returned for {ticker} between {start} and {end}")
    df = df.reset_index()

    # Serialize to CSV in-memory
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)

    # Create boto3 client (allow profile usage for dev)
    if aws_profile:
        session = boto3.Session(profile_name=aws_profile, region_name=region_name)
        s3 = session.client("s3")
    else:
        s3 = boto3.client("s3", region_name=region_name)

    key = _make_s3_key(prefix, ticker)
    s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer.getvalue())
    s3_uri = f"s3://{bucket}/{key}"
    s3a_uri = f"s3a://{bucket}/{key}"
    return {"key": key, "s3_uri": s3_uri, "s3a_uri": s3a_uri}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch ticker with yfinance and upload to S3")
    parser.add_argument("ticker")
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="forex")
    parser.add_argument("--aws-profile", default=None)
    parser.add_argument("--region", default=None)
    args = parser.parse_args()

    result = fetch_and_upload(
        args.ticker, args.start, args.end, args.bucket, args.prefix, aws_profile=args.aws_profile, region_name=args.region
    )
    print("Uploaded to:", result)
