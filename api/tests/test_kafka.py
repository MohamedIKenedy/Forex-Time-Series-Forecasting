import time
import threading
import logging
import sys
import os
import pytest
from kafka.errors import NoBrokersAvailable

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.kafka_service import KafkaService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def skip_if_no_kafka():
    """Skip all Kafka tests if Kafka is not available"""
    try:
        kafka_service = KafkaService(brokers=["localhost:9092"])
        kafka_service.create_producer()
        kafka_service.close()
    except NoBrokersAvailable:
        pytest.skip("Kafka not available, skipping Kafka tests")


# ============== TEST 1: Single Producer, Single Consumer ==============
def test_producer_consumer_simple():
    """Test basic produce and consume"""
    print("\n" + "=" * 60)
    print("TEST 1: Simple Producer-Consumer")
    print("=" * 60 + "\n")

    # Create service
    kafka_service = KafkaService(brokers=["localhost:9092"])

    # ---- Producer ----
    print("[PRODUCER] Sending 3 messages...")
    messages = [
        {"ticker": "EURUSD", "close": 1.0234, "timestamp": "2026-01-05T10:00:00"},
        {"ticker": "EURUSD", "close": 1.0240, "timestamp": "2026-01-05T10:01:00"},
        {"ticker": "EURUSD", "close": 1.0245, "timestamp": "2026-01-05T10:02:00"},
    ]

    for msg in messages:
        kafka_service.produce_message(topic="test-topic", message=msg, key="EURUSD")
        time.sleep(0.5)

    # ---- Consumer ----
    print("\n[CONSUMER] Reading messages (will read last 3)...\n")

    received_messages = []

    def collect_message(data):
        """Callback to collect messages"""
        received_messages.append(data)
        print(f"Received: {data}")

    kafka_consumer = KafkaService(
        brokers=["localhost:9092"], group_id="test-consumer-group"
    )

    # Set timeout so consumer doesn't run forever
    kafka_consumer.create_consumer(topics=["test-topic"], auto_offset_reset="earliest")

    count = 0
    for message in kafka_consumer.consumer:
        data = message.value
        collect_message(data)
        count += 1
        if count >= 3:
            break

    kafka_service.close()
    kafka_consumer.close()

    assert len(received_messages) == 3


# ============== TEST 2: Producer-Consumer in Separate Threads ==============
def test_producer_consumer_concurrent():
    """Test producer and consumer running simultaneously"""
    print("\n" + "=" * 60)
    print("TEST 2: Concurrent Producer-Consumer")
    print("=" * 60 + "\n")

    received_count = [0] 

    def producer_job():
        """Producer runs in separate thread"""
        kafka_service = KafkaService(brokers=["localhost:9092"])
        print("[PRODUCER THREAD] Starting to send messages...")

        for i in range(5):
            message = {
                "ticker": "GBPUSD",
                "close": 1.2500 + i * 0.0001,
                "timestamp": f"2026-01-05T11:{i:02d}:00",
            }
            kafka_service.produce_message(
                topic="concurrent-test", message=message, key="GBPUSD"
            )
            print(f"[PRODUCER THREAD] Sent message {i+1}/5")
            time.sleep(1)

        kafka_service.close()
        print("[PRODUCER THREAD] Done sending messages")

    def consumer_job():
        """Consumer runs in separate thread"""
        kafka_service = KafkaService(
            brokers=["localhost:9092"], group_id="concurrent-test-group"
        )
        kafka_service.create_consumer(
            topics=["concurrent-test"], auto_offset_reset="latest"
        )

        print("[CONSUMER THREAD] Waiting for messages...")

        for message in kafka_service.consumer:
            data = message.value
            received_count[0] += 1
            print(
                f"[CONSUMER THREAD] Received message {received_count[0]}: {data['ticker']}"
            )

            if received_count[0] >= 5:
                break

        kafka_service.close()
        print("[CONSUMER THREAD] Done consuming messages")

    # Start both threads
    producer_thread = threading.Thread(target=producer_job)
    consumer_thread = threading.Thread(target=consumer_job)

    producer_thread.start()
    time.sleep(0.5)
    consumer_thread.start()

    producer_thread.join()
    consumer_thread.join()

    assert received_count[0] == 5


# ============== TEST 3: Multiple Tickers with Keys ==============
def test_multiple_tickers():
    """Test multiple tickers going to same topic but different partitions"""

    print("\n" + "=" * 60)
    print("TEST 3: Multiple Tickers (Key-based Partitioning)")
    print("=" * 60 + "\n")

    kafka_service = KafkaService(brokers=["localhost:9092"])

    tickers = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

    print("[PRODUCER] Sending messages for multiple tickers...")
    for ticker in tickers:
        message = {
            "ticker": ticker,
            "close": 1.0000 + hash(ticker) % 1000 / 10000,
            "timestamp": "2026-01-05T12:00:00",
        }
        kafka_service.produce_message(
            topic="multi-ticker-test", message=message, key=ticker
        )
        print(f"Sent {ticker}")

    print("\n[CONSUMER] Reading messages...")

    kafka_consumer = KafkaService(
        brokers=["localhost:9092"], group_id="multi-ticker-group"
    )

    received = {}
    kafka_consumer.create_consumer(
        topics=["multi-ticker-test"], auto_offset_reset="earliest"
    )

    count = 0
    for message in kafka_consumer.consumer:
        data = message.value
        ticker = data["ticker"]
        received[ticker] = data
        print(f"Received {ticker} at partition {message.partition}")
        count += 1
        if count >= 4:
            break

    kafka_service.close()
    kafka_consumer.close()

    assert len(received) == 4


# ============== TEST 4: Error Handling ==============
def test_error_handling():
    """Test behavior when Kafka is unavailable"""
    print("\n" + "=" * 60)
    print("TEST 4: Error Handling (Invalid Broker)")
    print("=" * 60 + "\n")

    kafka_service = KafkaService(brokers=["invalid-broker:9092"])

    with pytest.raises(Exception):
        print("[TEST] Attempting to produce to invalid broker...")
        kafka_service.produce_message(topic="test-topic", message={"test": "data"})
