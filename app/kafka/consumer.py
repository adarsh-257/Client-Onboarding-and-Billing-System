"""Kafka consumer workers for processing events across microservices."""
import json
import logging
import signal
import threading
from confluent_kafka import Consumer, KafkaError

from app.kafka.topics import ALL_TOPICS
from app.kafka.handlers import handle_event

logger = logging.getLogger(__name__)


class KafkaConsumerWorker:
    """
    A Kafka consumer that runs in a background thread,
    processing events from subscribed topics.
    """

    def __init__(self, app, bootstrap_servers='localhost:9092', group_id='onboarding-system'):
        self.app = app
        self.running = False
        self.thread = None
        self.consumer = None
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id

    def start(self):
        """Start the consumer in a background thread."""
        if self.running:
            logger.warning("Consumer already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._consume, daemon=True)
        self.thread.start()
        logger.info("Kafka consumer worker started")

    def stop(self):
        """Gracefully stop the consumer."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        if self.consumer:
            self.consumer.close()
        logger.info("Kafka consumer worker stopped")

    def _consume(self):
        """Main consumer loop."""
        try:
            self.consumer = Consumer({
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': self.group_id,
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': True,
                'auto.commit.interval.ms': 5000,
            })

            self.consumer.subscribe(ALL_TOPICS)
            logger.info(f"Subscribed to topics: {ALL_TOPICS}")

            while self.running:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue

                try:
                    topic = msg.topic()
                    value = json.loads(msg.value().decode('utf-8'))
                    key = msg.key().decode('utf-8') if msg.key() else None

                    logger.info(
                        f"Received message from topic '{topic}': "
                        f"event_type={value.get('event_type')}"
                    )

                    # Handle the event within Flask app context
                    with self.app.app_context():
                        handle_event(topic, value, key)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message from {msg.topic()}: {e}")

        except Exception as e:
            logger.error(f"Consumer initialization failed: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
            logger.info("Consumer loop ended")


def start_consumer(app):
    """
    Start a Kafka consumer worker for the given Flask app.
    Returns the worker instance for lifecycle management.
    """
    config = app.config
    worker = KafkaConsumerWorker(
        app=app,
        bootstrap_servers=config.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        group_id=config.get('KAFKA_GROUP_ID', 'onboarding-system'),
    )
    worker.start()

    # Register shutdown handler
    def shutdown_handler(signum, frame):
        worker.stop()

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    return worker
