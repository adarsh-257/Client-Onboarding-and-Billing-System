"""
Setup Kafka topics for the onboarding system.
Run: python scripts/setup_kafka_topics.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from confluent_kafka.admin import AdminClient, NewTopic

from app.kafka.topics import ALL_TOPICS


def setup_topics(bootstrap_servers='localhost:9092'):
    """Create all required Kafka topics."""
    print("\n📡 Setting up Kafka topics...\n")

    admin = AdminClient({'bootstrap.servers': bootstrap_servers})

    # List existing topics
    metadata = admin.list_topics(timeout=10)
    existing = set(metadata.topics.keys())

    topics_to_create = []
    for topic_name in ALL_TOPICS:
        if topic_name not in existing:
            topics_to_create.append(
                NewTopic(
                    topic=topic_name,
                    num_partitions=3,
                    replication_factor=1,
                )
            )
            print(f"  + Creating topic: {topic_name}")
        else:
            print(f"  ✓ Topic exists: {topic_name}")

    if topics_to_create:
        futures = admin.create_topics(topics_to_create)
        for topic, future in futures.items():
            try:
                future.result()
                print(f"  ✅ Created: {topic}")
            except Exception as e:
                print(f"  ❌ Failed to create {topic}: {e}")
    else:
        print("\n  All topics already exist!")

    print(f"\n🎉 Kafka topic setup complete! ({len(ALL_TOPICS)} topics)")
    print(f"   Kafka UI available at: http://localhost:8080\n")


if __name__ == '__main__':
    bootstrap = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    setup_topics(bootstrap)
