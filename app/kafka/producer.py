"""Kafka message producer — thread-safe singleton."""
import json
import logging
from datetime import datetime, timezone
from confluent_kafka import Producer

logger = logging.getLogger(__name__)

_producer_instance = None


def get_producer(bootstrap_servers='localhost:9092'):
    """Get or create a thread-safe Kafka producer singleton."""
    global _producer_instance
    if _producer_instance is None:
        try:
            _producer_instance = Producer({
                'bootstrap.servers': bootstrap_servers,
                'client.id': 'onboarding-system-producer',
                'acks': 'all',
                'retries': 3,
                'retry.backoff.ms': 500,
            })
            logger.info(f"Kafka producer connected to {bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            return None
    return _producer_instance


def _delivery_callback(err, msg):
    """Callback for message delivery confirmation."""
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(
            f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}"
        )


def publish_event(topic, event_type, data, key=None, bootstrap_servers='localhost:9092'):
    """
    Publish an event to a Kafka topic.

    Args:
        topic: Kafka topic name
        event_type: Type of event (e.g., 'client.onboarded')
        data: Event payload (dict)
        key: Optional message key for partitioning
        bootstrap_servers: Kafka broker address
    """
    producer = get_producer(bootstrap_servers)
    if producer is None:
        logger.warning(f"Kafka producer unavailable. Event '{event_type}' not published.")
        return False

    message = {
        'event_type': event_type,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': data,
    }

    try:
        producer.produce(
            topic=topic,
            key=str(key).encode('utf-8') if key else None,
            value=json.dumps(message, default=str).encode('utf-8'),
            callback=_delivery_callback,
        )
        producer.poll(0)  # Trigger delivery callbacks
        logger.info(f"Event '{event_type}' published to topic '{topic}'")
        return True
    except Exception as e:
        logger.error(f"Failed to publish event '{event_type}': {e}")
        return False


def flush_producer():
    """Flush pending messages (call on shutdown)."""
    global _producer_instance
    if _producer_instance:
        _producer_instance.flush(timeout=10)
        logger.info("Kafka producer flushed")
