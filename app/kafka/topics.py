"""Kafka topic constants."""

# Topic names for event streaming
TOPICS = {
    'CLIENT_ONBOARDED': 'client.onboarded',
    'CLIENT_UPDATED': 'client.updated',
    'SUBSCRIPTION_CREATED': 'subscription.created',
    'SUBSCRIPTION_CANCELLED': 'subscription.cancelled',
    'INVOICE_GENERATED': 'invoice.generated',
    'INVOICE_PAID': 'invoice.paid',
    'DOCUMENT_UPLOADED': 'document.uploaded',
    'DOCUMENT_DELETED': 'document.deleted',
    'ERROR_DETECTED': 'error.detected',
    'NOTIFICATION_SENT': 'notification.sent',
}

# All topic names as a list (for setup script)
ALL_TOPICS = list(TOPICS.values())
