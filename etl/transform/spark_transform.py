"""PySpark job to transform raw yfinance CSVs on S3 into partitioned Parquet.

Usage (spark-submit):
  spark-submit spark_transform.py --input s3a://my-bucket/forex/raw/ --output s3a://my-bucket/forex/processed/
"""
import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import input_file_name, regexp_extract, to_date, col


def normalize_columns(df):
    # Lowercase column names and standardize adj close
    cols = df.columns
    rename_map = {}
    for c in cols:
        lc = c.strip()
        if lc.lower() == "adj close":
            rename_map[c] = "adj_close"
        else:
            rename_map[c] = lc.replace(" ", "_").lower()
    for old, new in rename_map.items():
        if old != new:
            df = df.withColumnRenamed(old, new)
    return df


def main(input_path: str, output_path: str, default_ticker: str | None = None):
    spark = SparkSession.builder.appName("forex-transform").getOrCreate()

    df = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .option("recursiveFileLookup", True)
        .csv(input_path)
    )

    if df.rdd.isEmpty():
        print("No files found under", input_path)
        spark.stop()
        return

    df = df.withColumn("source_file", input_file_name())
    # Try to extract ticker from path like .../raw/{ticker}/ingest_date=...
    df = df.withColumn("ticker_extracted", regexp_extract(col("source_file"), r"raw/([^/]+)/", 1))
    if default_ticker:
        df = df.withColumn("ticker", col("ticker_extracted")).na.fill({"ticker": default_ticker})
    else:
        df = df.withColumn("ticker", col("ticker_extracted"))

    df = normalize_columns(df)

    # Ensure date column exists
    if "date" not in df.columns:
        # try common alternatives
        for cand in ("timestamp", "datetime"):
            if cand in df.columns:
                df = df.withColumnRenamed(cand, "date")
                break

    df = df.withColumn("date", to_date(col("date")))

    # select canonical columns if present
    select_cols = [c for c in ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"] if c in df.columns]
    df_out = df.select(*select_cols)

    (df_out.write.mode("append").partitionBy("ticker", "date").parquet(output_path))

    spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ticker", default=None)
    args = parser.parse_args()
    main(args.input, args.output, args.ticker)
