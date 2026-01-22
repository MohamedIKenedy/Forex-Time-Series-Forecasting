"""Load processed parquet from S3 into a SQL database (Postgres/Redshift-compatible).

Helpers intended for the ETL `load` stage (moved from api/services).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text


def load_parquet_to_postgres(s3_path: str, table: str, pg_uri: str, storage_options: Optional[dict] = None) -> int:
    """Read parquet from `s3_path` and insert into `table` at `pg_uri`.

    Returns number of rows inserted.
    """
    storage_options = storage_options or {}
    df = pd.read_parquet(s3_path, engine="pyarrow", storage_options=storage_options)
    if df.empty:
        return 0
    engine = create_engine(pg_uri)
    # to_sql returns None for modern pandas; use len(df) as inserted rows
    df.to_sql(table, engine, if_exists="append", index=False)
    return len(df)


def load_parquet_to_postgres_upsert(
    s3_path: str,
    table: str,
    pg_uri: str,
    key_columns: Optional[list[str]] = None,
    storage_options: Optional[dict] = None,
) -> int:
    """Read parquet from `s3_path`, write to a staging table, then upsert into target `table`.

    Uses a staging table and a single SQL `INSERT ... ON CONFLICT` to perform upsert
    based on `key_columns` (defaults to ['ticker','date']). Returns number of rows processed.
    """
    storage_options = storage_options or {}
    key_columns = key_columns or ["ticker", "date"]

    df = pd.read_parquet(s3_path, engine="pyarrow", storage_options=storage_options)
    if df.empty:
        return 0

    engine = create_engine(pg_uri)
    staging_table = f"{table.replace('.', '_')}_staging"

    # write staging table (replace)
    df.to_sql(staging_table, engine, if_exists="replace", index=False, method="multi")

    cols = list(df.columns)
    cols_sql = ", ".join(cols)
    select_cols = ", ".join([f"{c}" for c in cols])

    # columns used for conflict target
    pk = ", ".join(key_columns)

    # build update set for non-pk columns
    non_pk = [c for c in cols if c not in key_columns]
    if non_pk:
        update_sql = ", ".join([f"{c}=EXCLUDED.{c}" for c in non_pk])
    else:
        update_sql = ""

    insert_sql = f"INSERT INTO {table} ({cols_sql}) SELECT {select_cols} FROM {staging_table} "
    if update_sql:
        insert_sql += f"ON CONFLICT ({pk}) DO UPDATE SET {update_sql};"
    else:
        insert_sql += f"ON CONFLICT ({pk}) DO NOTHING;"

    with engine.begin() as conn:
        conn.execute(text(insert_sql))
        # drop staging table
        conn.execute(text(f"DROP TABLE IF EXISTS {staging_table}"))

    return len(df)
