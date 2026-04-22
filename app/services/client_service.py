"""Client service — handles client onboarding and management."""
import logging
from datetime import datetime, timezone

from app.extensions import db
from app.models.client import Client, ClientStatus
from app.kafka.producer import publish_event
from app.kafka.topics import TOPICS

logger = logging.getLogger(__name__)


def onboard_client(data):
    """
    Onboard a new client.

    1. Create client record
    2. Activate the account
    3. Publish 'client.onboarded' Kafka event
    4. The Kafka handler will auto-create a default subscription

    Args:
        data: dict with client details

    Returns:
        Client instance
    """
    client = Client(
        company_name=data['company_name'],
        contact_name=data['contact_name'],
        email=data['email'],
        phone=data.get('phone'),
        address=data.get('address'),
        city=data.get('city'),
        state=data.get('state'),
        country=data.get('country', 'US'),
        industry=data.get('industry'),
        company_size=data.get('company_size'),
        status=ClientStatus.ACTIVE,
        onboarded_at=datetime.now(timezone.utc),
        notes=data.get('notes'),
    )

    db.session.add(client)
    db.session.commit()

    logger.info(f"Client onboarded: {client.company_name} (ID: {client.id})")

    # Publish Kafka event
    publish_event(
        topic=TOPICS['CLIENT_ONBOARDED'],
        event_type='client.onboarded',
        data={
            'client_id': client.id,
            'company_name': client.company_name,
            'email': client.email,
            'industry': client.industry,
        },
        key=client.id,
    )

    return client


def get_clients(page=1, per_page=20, status=None, search=None, industry=None):
    """
    Get paginated client list with optional filters.

    Args:
        page: Page number (1-indexed)
        per_page: Items per page
        status: Filter by status
        search: Search by company name or email
        industry: Filter by industry

    Returns:
        dict with items, total, pages, current_page
    """
    query = Client.query

    if status:
        if isinstance(status, str):
            status = ClientStatus(status)
        query = query.filter(Client.status == status)

    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            db.or_(
                Client.company_name.ilike(search_filter),
                Client.email.ilike(search_filter),
                Client.contact_name.ilike(search_filter),
            )
        )

    if industry:
        query = query.filter(Client.industry == industry)

    query = query.order_by(Client.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        'items': [c.to_dict() for c in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    }


def get_client(client_id):
    """Get a single client by ID."""
    return Client.query.get_or_404(client_id)


def update_client(client_id, data):
    """Update client details."""
    client = Client.query.get_or_404(client_id)

    updatable_fields = [
        'company_name', 'contact_name', 'email', 'phone',
        'address', 'city', 'state', 'country', 'industry',
        'company_size', 'notes',
    ]

    changes = {}
    for field in updatable_fields:
        if field in data and getattr(client, field) != data[field]:
            changes[field] = {'old': getattr(client, field), 'new': data[field]}
            setattr(client, field, data[field])

    if changes:
        db.session.commit()

        publish_event(
            topic=TOPICS['CLIENT_UPDATED'],
            event_type='client.updated',
            data={
                'client_id': client.id,
                'changes': changes,
            },
            key=client.id,
        )

        logger.info(f"Client {client.id} updated: {list(changes.keys())}")

    return client


def update_client_status(client_id, new_status):
    """Update client status with validation."""
    client = Client.query.get_or_404(client_id)

    if isinstance(new_status, str):
        new_status = ClientStatus(new_status)

    # Valid transitions
    valid_transitions = {
        ClientStatus.PENDING: [ClientStatus.ACTIVE, ClientStatus.ARCHIVED],
        ClientStatus.ACTIVE: [ClientStatus.SUSPENDED, ClientStatus.ARCHIVED],
        ClientStatus.SUSPENDED: [ClientStatus.ACTIVE, ClientStatus.ARCHIVED],
        ClientStatus.ARCHIVED: [ClientStatus.ACTIVE],
    }

    allowed = valid_transitions.get(client.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from {client.status.value} to {new_status.value}. "
            f"Allowed: {[s.value for s in allowed]}"
        )

    old_status = client.status.value
    client.status = new_status

    if new_status == ClientStatus.ACTIVE and not client.onboarded_at:
        client.onboarded_at = datetime.now(timezone.utc)

    db.session.commit()

    publish_event(
        topic=TOPICS['CLIENT_UPDATED'],
        event_type='client.status_changed',
        data={
            'client_id': client.id,
            'old_status': old_status,
            'new_status': new_status.value,
        },
        key=client.id,
    )

    logger.info(f"Client {client.id} status: {old_status} → {new_status.value}")
    return client


def get_dashboard_stats():
    """Get statistics for the dashboard."""
    from app.models.subscription import Subscription, SubscriptionStatus
    from app.models.invoice import Invoice, InvoiceStatus
    from app.models.document import Document

    total_clients = Client.query.count()
    active_clients = Client.query.filter(Client.status == ClientStatus.ACTIVE).count()
    pending_clients = Client.query.filter(Client.status == ClientStatus.PENDING).count()

    active_subscriptions = Subscription.query.filter(
        Subscription.status == SubscriptionStatus.ACTIVE
    ).count()

    total_revenue = db.session.query(
        db.func.coalesce(db.func.sum(Invoice.total), 0)
    ).filter(Invoice.status == InvoiceStatus.PAID).scalar()

    pending_invoices = Invoice.query.filter(
        Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.DRAFT])
    ).count()

    overdue_invoices = Invoice.query.filter(
        Invoice.status == InvoiceStatus.OVERDUE
    ).count()

    total_documents = Document.query.filter(Document.is_deleted == False).count()

    # Recent activity (last 10 clients)
    recent_clients = Client.query.order_by(
        Client.created_at.desc()
    ).limit(10).all()

    return {
        'total_clients': total_clients,
        'active_clients': active_clients,
        'pending_clients': pending_clients,
        'active_subscriptions': active_subscriptions,
        'total_revenue': float(total_revenue),
        'pending_invoices': pending_invoices,
        'overdue_invoices': overdue_invoices,
        'total_documents': total_documents,
        'recent_clients': [c.to_dict() for c in recent_clients],
    }


def get_all_industries():
    """Get list of unique industries."""
    industries = db.session.query(Client.industry).distinct().filter(
        Client.industry.isnot(None)
    ).all()
    return sorted([i[0] for i in industries if i[0]])
