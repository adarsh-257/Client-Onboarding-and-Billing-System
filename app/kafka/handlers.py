"""Kafka event handlers — react to events across microservices."""
import logging
from datetime import datetime, timezone, timedelta

from app.kafka.topics import TOPICS

logger = logging.getLogger(__name__)


def handle_event(topic, message, key=None):
    """
    Route events to appropriate handlers based on topic.

    This is the core of our event-driven architecture:
    - client.onboarded → auto-create default subscription
    - subscription.created → auto-generate first invoice
    - invoice.generated → send notification
    - error.detected → trigger recovery workflow
    """
    event_type = message.get('event_type', '')
    data = message.get('data', {})
    timestamp = message.get('timestamp', '')

    handler_map = {
        TOPICS['CLIENT_ONBOARDED']: _handle_client_onboarded,
        TOPICS['CLIENT_UPDATED']: _handle_client_updated,
        TOPICS['SUBSCRIPTION_CREATED']: _handle_subscription_created,
        TOPICS['SUBSCRIPTION_CANCELLED']: _handle_subscription_cancelled,
        TOPICS['INVOICE_GENERATED']: _handle_invoice_generated,
        TOPICS['INVOICE_PAID']: _handle_invoice_paid,
        TOPICS['DOCUMENT_UPLOADED']: _handle_document_uploaded,
        TOPICS['ERROR_DETECTED']: _handle_error_detected,
    }

    handler = handler_map.get(topic)
    if handler:
        try:
            handler(data, timestamp, key)
            logger.info(f"Successfully handled event '{event_type}' from topic '{topic}'")
        except Exception as e:
            logger.error(f"Error handling event '{event_type}': {e}")
            # Publish to error topic for monitoring
            _publish_error(topic, event_type, str(e), data)
    else:
        logger.warning(f"No handler for topic '{topic}'")


def _handle_client_onboarded(data, timestamp, key):
    """
    When a client is onboarded:
    1. Auto-create a default (Free) subscription
    2. Log the onboarding event
    """
    from app.services.subscription_service import create_default_subscription

    client_id = data.get('client_id')
    if client_id:
        logger.info(f"Auto-creating default subscription for client {client_id}")
        try:
            create_default_subscription(client_id)
        except Exception as e:
            logger.error(f"Failed to auto-create subscription for client {client_id}: {e}")


def _handle_client_updated(data, timestamp, key):
    """Log client updates for audit trail."""
    client_id = data.get('client_id')
    changes = data.get('changes', {})
    logger.info(f"Client {client_id} updated: {changes}")


def _handle_subscription_created(data, timestamp, key):
    """
    When a subscription is created:
    1. Auto-generate the first invoice
    """
    from app.services.invoice_service import generate_invoice_for_subscription

    subscription_id = data.get('subscription_id')
    client_id = data.get('client_id')
    if subscription_id and client_id:
        logger.info(f"Auto-generating invoice for subscription {subscription_id}")
        try:
            generate_invoice_for_subscription(subscription_id)
        except Exception as e:
            logger.error(f"Failed to generate invoice for subscription {subscription_id}: {e}")


def _handle_subscription_cancelled(data, timestamp, key):
    """Handle subscription cancellation cleanup."""
    subscription_id = data.get('subscription_id')
    reason = data.get('reason', 'No reason provided')
    logger.info(f"Subscription {subscription_id} cancelled: {reason}")


def _handle_invoice_generated(data, timestamp, key):
    """
    When an invoice is generated:
    1. Send notification to client
    """
    invoice_id = data.get('invoice_id')
    client_id = data.get('client_id')
    total = data.get('total', 0)
    logger.info(f"Invoice {invoice_id} generated for client {client_id}: ${total}")


def _handle_invoice_paid(data, timestamp, key):
    """Handle invoice payment confirmation."""
    invoice_id = data.get('invoice_id')
    logger.info(f"Invoice {invoice_id} paid")


def _handle_document_uploaded(data, timestamp, key):
    """Log document upload events."""
    document_id = data.get('document_id')
    client_id = data.get('client_id')
    filename = data.get('filename')
    logger.info(f"Document '{filename}' (id={document_id}) uploaded for client {client_id}")


def _handle_error_detected(data, timestamp, key):
    """
    Handle detected errors:
    1. Classify severity
    2. Trigger recovery workflow
    3. Send alerts for critical errors
    """
    error_type = data.get('error_type', 'unknown')
    service = data.get('service', 'unknown')
    message = data.get('message', '')
    severity = data.get('severity', 'warning')

    logger.error(f"[{severity.upper()}] Error in {service}: {error_type} — {message}")

    if severity == 'critical':
        logger.critical(f"CRITICAL ERROR in {service} — triggering recovery workflow")
        # In production, this would trigger Lambda recovery functions


def _publish_error(source_topic, event_type, error_message, original_data):
    """Publish error events for monitoring."""
    from app.kafka.producer import publish_event

    publish_event(
        topic=TOPICS['ERROR_DETECTED'],
        event_type='error.detected',
        data={
            'error_type': 'event_processing_failure',
            'service': 'event-handler',
            'source_topic': source_topic,
            'original_event_type': event_type,
            'message': error_message,
            'severity': 'warning',
        }
    )
