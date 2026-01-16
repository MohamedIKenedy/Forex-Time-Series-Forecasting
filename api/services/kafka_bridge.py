from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Iterable, Optional

from config import settings

try:
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError, NoBrokersAvailable
except Exception:  
    KafkaConsumer = None
    KafkaError = Exception
    NoBrokersAvailable = Exception


MessageHandler = Callable[[Dict[str, Any]], None]


class KafkaWebSocketBridge:
    """Consumes Kafka topics in a background thread and forwards messages.

    This lets the UI chart be driven by Kafka (producer -> broker -> consumer -> WS broadcast).
    """

    def __init__(self, on_message: MessageHandler, group_id: str = "forex-ws-bridge"):
        self._on_message = on_message
        self._group_id = group_id
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._consumer: Optional[Any] = None
        self._topics: list[str] = []

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def topics(self) -> list[str]:
        return list(self._topics)

    def start(self, topics: Iterable[str]) -> None:
        if self.is_running:
            return

        if KafkaConsumer is None:
            raise RuntimeError("kafka-python is not installed in the API environment")

        self._topics = list(topics)
        if not self._topics:
            raise ValueError("No topics provided")

        self._stop_event.clear()
        try:
            self._consumer = KafkaConsumer(
                *self._topics,
                bootstrap_servers=settings.kafka_brokers,
                group_id=self._group_id,
                value_deserializer=lambda m: __import__("json").loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                consumer_timeout_ms=1000,
                session_timeout_ms=6000,
                heartbeat_interval_ms=2000,
                request_timeout_ms=30000,
                api_version_auto_timeout_ms=10000,
            )
        except NoBrokersAvailable as e:
            self._consumer = None
            raise RuntimeError(f"Kafka not reachable: {e}")
        except KafkaError as e:
            self._consumer = None
            raise RuntimeError(f"Kafka error: {e}")

        self._thread = threading.Thread(target=self._run, name="kafka-ws-bridge", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        consumer = self._consumer
        if consumer is not None:
            try:
                consumer.close()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None
        self._consumer = None
        self._topics = []

    def _run(self) -> None:
        if self._consumer is None:
            return

        while not self._stop_event.is_set():
            try:
                for msg in self._consumer:
                    if self._stop_event.is_set():
                        break
                    try:
                        value = msg.value
                        if isinstance(value, dict):
                            self._on_message(value)
                    except Exception as e:
                        print(f"[Kafka Bridge] Message processing error: {e}")
                        continue
            except Exception as e:
                print(f"[Kafka Bridge] Consumer error: {e}")
                time.sleep(0.25)

        try:
            self._consumer.close()
        except Exception:
            pass
