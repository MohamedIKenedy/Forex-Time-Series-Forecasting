import builtins
from io import StringIO

import pytest


class DummyDF:
    def __init__(self):
        self._data = [["2025-01-01", 1, 2, 3, 4, 4, 1000]]

    def reset_index(self):
        return self

    def empty(self):
        return False

    def to_csv(self, buf, index=False):
        buf.write("Date,Open,High,Low,Close,Adj Close,Volume\n2025-01-01,1,2,3,4,4,1000\n")


def test_fetch_and_upload_monkeypatch(monkeypatch, tmp_path):
    # mock yfinance.download
    def fake_download(ticker, start, end, progress=False):
        return DummyDF()

    class DummyS3Client:
        def __init__(self):
            self.last = {}

        def put_object(self, Bucket, Key, Body):
            self.last = {"Bucket": Bucket, "Key": Key, "Body": Body}

    monkeypatch.setattr("etl.extract.yfinance_s3.yf.download", fake_download)
    monkeypatch.setattr("etl.extract.yfinance_s3.boto3.client", lambda *args, **kwargs: DummyS3Client())

    from etl.extract.yfinance_s3 import fetch_and_upload

    result = fetch_and_upload("EURUSD=X", "2025-01-01", "2025-01-02", bucket="my-bucket", prefix="forex-test")
    assert isinstance(result, dict)
    assert "s3_uri" in result and "s3a_uri" in result
    assert "forex-test/raw/EURUSD=X/ingest_date=" in result["s3_uri"]
