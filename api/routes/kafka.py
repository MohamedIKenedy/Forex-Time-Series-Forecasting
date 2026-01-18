from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List, Optional

from config import settings

try:
    # kafka-python
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError, NoBrokersAvailable
except Exception:  # pragma: no cover
    KafkaConsumer = None
    KafkaError = Exception
    NoBrokersAvailable = Exception


router = APIRouter()


def _architecture_diagram(brokers: List[str]) -> str:
    brokers_str = ", ".join(brokers) if brokers else "(not configured)"
    return "\n".join(
        [
            "Forex Platform (Kafka + Streaming)",
            "",
            "  [UI: forex-dash]",
            "        |",
            "        |  WebSocket (price_update)",
            "        v",
            "  [FastAPI /stream/ws]  <--- live pushes",
            "        ^",
            "        |",
            "        |  callbacks on every fetch",
            "        |",
            "  [StreamingService]",
            "        |\\ ",
            "        | \\ produce candles",
            "        |  \\ (instant / hourly / daily)",
            "        v   v",
            f"  [Kafka broker(s): {brokers_str}]",
            "        |",
            "        |  topics:",
            "        |   - instant_<ticker>",
            "        |   - hourly_<ticker>",
            "        |   - daily_<ticker>",
        ]
    )


def _get_consumer():
    if KafkaConsumer is None:
        raise HTTPException(
            status_code=500,
            detail="kafka-python is not available in this API environment.",
        )

    try:
        return KafkaConsumer(
            bootstrap_servers=settings.kafka_brokers,
            enable_auto_commit=False,
            group_id=None,
            api_version_auto_timeout_ms=5000,
            request_timeout_ms=5000,
            consumer_timeout_ms=2000,
        )
    except NoBrokersAvailable as e:
        raise HTTPException(status_code=503, detail=f"Kafka not reachable: {e}")
    except KafkaError as e:
        raise HTTPException(status_code=503, detail=f"Kafka error: {e}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create Kafka consumer: {e}"
        )


@router.get("/diagram")
async def get_kafka_diagram() -> Dict[str, Any]:
    return {
        "brokers": settings.kafka_brokers,
        "diagram": _architecture_diagram(settings.kafka_brokers),
    }


@router.get("/health")
async def kafka_health() -> Dict[str, Any]:
    consumer = _get_consumer()
    try:
        topics = sorted(list(consumer.topics()))
        return {
            "ok": True,
            "brokers": settings.kafka_brokers,
            "topics_count": len(topics),
        }
    finally:
        try:
            consumer.close()
        except Exception:
            pass


@router.get("/topics")
async def kafka_topics(prefix: Optional[str] = None) -> Dict[str, Any]:
    consumer = _get_consumer()
    try:
        topics = sorted(list(consumer.topics()))
        if prefix:
            topics = [t for t in topics if t.startswith(prefix)]

        topic_rows: List[Dict[str, Any]] = []
        for t in topics:
            partitions = consumer.partitions_for_topic(t) or set()
            topic_rows.append({"topic": t, "partitions": len(partitions)})

        return {
            "brokers": settings.kafka_brokers,
            "topics": topic_rows,
        }
    finally:
        try:
            consumer.close()
        except Exception:
            pass
