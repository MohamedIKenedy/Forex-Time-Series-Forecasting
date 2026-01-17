from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic, NewPartitions
from kafka.errors import KafkaError, TopicAlreadyExistsError
import json
import logging
from typing import Any, Dict, Callable, Optional
import zlib

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class KafkaService:
    """ Kafka Service class to handle producer and consumer ops for forex data in real-time """
    def __init__(
        self,
        brokers: list = ['localhost:9092'],
        group_id: str | None = None,
        topic_partitions: int = 10         
    ):
        """ Init the kafka service with broker connection
            Args:
                - List of brokers
                - Consumer group name

         """
        self.brokers = brokers
        self.group_id = group_id
        self.producer = None
        self.consumer = None
        self.admin: KafkaAdminClient | None = None
        self.topic_partitions = max(1, int(topic_partitions))

        
    def create_producer(self) -> KafkaProducer:
        """ Create a Kafka Producer for publishing messages """
        if self.producer is None:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers = self.brokers,
                    value_serializer = lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',
                    retries = 3,
                    max_in_flight_requests_per_connection = 1
                )
                logger.info("Kafka producer successfully created")
            except KafkaError as e:
                logger.error(f"Failed to create Kafka Producer: {e}")
                raise

    def _create_admin(self):
        if self.admin is None:
            try:
                self.admin = KafkaAdminClient(bootstrap_servers=self.brokers)
            except KafkaError as e:
                logger.warning(f"Kafka admin not available: {e}")
                self.admin = None

    def ensure_partitions(self, topic: str):
        """Ensure the topic exists and has at least topic_partitions partitions."""
        self._create_admin()
        if self.admin is None:
            return
        try:
            # Try describe first
            desc = self.admin.describe_topics([topic])
            current = desc[0].get("partitions") or []
            if len(current) >= self.topic_partitions:
                return
            try:
                self.admin.create_partitions({topic: NewPartitions(total_count=self.topic_partitions)})
                logger.info(f"Expanded topic {topic} to {self.topic_partitions} partitions")
            except TopicAlreadyExistsError:
                return
        except KafkaError:
            # Try create if describe failed
            try:
                new_topic = NewTopic(name=topic, num_partitions=self.topic_partitions, replication_factor=1)
                self.admin.create_topics([new_topic])
                logger.info(f"Created topic {topic} with {self.topic_partitions} partitions")
            except TopicAlreadyExistsError:
                return
            except KafkaError as e:
                logger.warning(f"Unable to ensure partitions for {topic}: {e}")

    def produce_message(self, topic: str, message: Dict[str,Any], key: str | None = None):
        """ Send a message to a kafka topic """
        if self.producer is None:
            self.create_producer()

        try:
            key_bytes = key.encode('utf-8') if key else None

            # Make sure the topic has multiple partitions and route deterministically by ticker key.
            self.ensure_partitions(topic)
            partition_id = None
            if key_bytes is not None:
                partition_id = zlib.crc32(key_bytes) % self.topic_partitions

            # Send messages in an async manner (That's me writing hahaha)
            future = self.producer.send(
                topic,
                value = message,
                key = key_bytes,
                partition = partition_id
            )

            metadata = future.get(timeout=10)

            # Downgraded to debug to reduce log noise in instant mode.
            logger.debug(
                f"Message sent to {topic} | "
                f"Partition: {metadata.partition} | "
                f"Offset: {metadata.offset}"
            )

        except KafkaError as e:
            logger.error(f"Failed to send msg: {e}")

    

    def create_consumer(self, topics: list, auto_offset_reset: str = 'latest') -> KafkaConsumer:
        """ Create a kafka consumer to read msgs from topics """
        if self.consumer is None:
            try:
                self.consumer = KafkaConsumer(
                    *topics,
                    bootstrap_servers = self.brokers,
                    group_id = self.group_id,
                    value_deserializer = lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset = auto_offset_reset,
                    enable_auto_commit = True,
                    auto_commit_interval_ms = 5000
                )
                logger.info(f"Kafka Consumer created for topics: {topics} | Group: {self.group_id}")
            except KafkaError as e:
                logger.error(f"Failed to create consumer: {e}")
                raise

        return self.consumer
    
    def consume_messages(self, topics: list, callback: Callable[[Dict[str, Any]],None]):
        """ Continuously consume messages from topics and process them """
        if self.consumer is None:
            self.create_consumer

        logger.info(f"Starting to consume messages from {topics}...")

        try:
            for message in self.consumer:
                logger.info(
                    f"Received message from {message.topic} | "
                    f"Partition: {message.partition} | "
                    f"Offset: {message.offset}"
                )
                
                data = message.value
                
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        except KafkaError as e:
            logger.error(f"Kafka consumer error: {e}")
        finally:
            self.close()

        
    def close(self):
        """ Gracefully shut producer & Consumer down to flush any pending msgs in producer buffer """
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Producer closed")
        
        if self.consumer:
            self.consumer.close()
            logger.info("Consumer closed")


