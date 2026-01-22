import os
import tempfile
import sqlite3
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from etl.load.load_to_sql import load_parquet_to_postgres_upsert


def make_sample_df():
    return pd.DataFrame(
        {
            "ticker": ["EURUSD"],
            "date": ["2025-01-01"],
            "open": [1.0],
            "high": [2.0],
            "low": [0.9],
            "close": [1.5],
            "adj_close": [1.5],
            "volume": [1000],
        }
    )


def create_target_table_sqlite(db_path: str, table_name: str):
    engine = create_engine(f"sqlite:///{db_path}")
    # create table with unique constraint on (ticker,date)
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ticker TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date)
            );
        """
            )
        )


def test_upsert_local_parquet(tmp_path: Path):
    # Prepare parquet file
    df = make_sample_df()
    parquet_path = tmp_path / "data.parquet"
    df.to_parquet(parquet_path, index=False)

    # Prepare sqlite DB file
    db_file = tmp_path / "test_db.sqlite"
    create_target_table_sqlite(str(db_file), "forex_prices")

    # Run upsert loader (uses pandas.read_parquet; accepts local path)
    rows = load_parquet_to_postgres_upsert(str(parquet_path), "forex_prices", f"sqlite:///{db_file}")
    assert rows == 1

    # Verify row exists and values match
    engine = create_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        res = conn.execute(text("SELECT ticker, date, close FROM forex_prices")).fetchall()
        assert len(res) == 1
        assert res[0][0] == "EURUSD"
        assert float(res[0][2]) == 1.5

    # Run upsert again with updated close to test update path
    df2 = make_sample_df()
    df2.loc[0, "close"] = 2.0
    parquet_path2 = tmp_path / "data2.parquet"
    df2.to_parquet(parquet_path2, index=False)
    rows2 = load_parquet_to_postgres_upsert(str(parquet_path2), "forex_prices", f"sqlite:///{db_file}")
    assert rows2 == 1

    with engine.connect() as conn:
        res2 = conn.execute(text("SELECT close FROM forex_prices WHERE ticker='EURUSD' AND date='2025-01-01' ")).fetchone()
        assert float(res2[0]) == 2.0
