"""Invoice service — handles invoice generation, PDF creation, and payment tracking."""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.invoice import Invoice, LineItem, InvoiceStatus
from app.models.subscription import Subscription
from app.models.client import Client
from app.kafka.producer import publish_event
from app.kafka.topics import TOPICS

logger = logging.getLogger(__name__)


def generate_invoice(client_id, line_items_data, due_days=30, notes=None, subscription_id=None, tax_rate=None):
    """
    Generate a new invoice for a client.

    Args:
        client_id: Client ID
        line_items_data: List of dicts with description, quantity, unit_price
        due_days: Days until invoice is due
        notes: Optional invoice notes
        subscription_id: Optional linked subscription
        tax_rate: Tax rate override (default from config)

    Returns:
        Invoice instance
    """
    from flask import current_app

    client = Client.query.get_or_404(client_id)

    if tax_rate is None:
        tax_rate = Decimal(str(current_app.config.get('INVOICE_TAX_RATE', 0.10)))

    # Generate unique invoice number
    invoice_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:8].upper()}"

    invoice = Invoice(
        client_id=client_id,
        subscription_id=subscription_id,
        invoice_number=invoice_number,
        status=InvoiceStatus.DRAFT,
        tax_rate=tax_rate,
        due_date=datetime.now(timezone.utc) + timedelta(days=due_days),
        notes=notes,
    )

    db.session.add(invoice)
    db.session.flush()  # Get invoice ID

    # Create line items
    for item_data in line_items_data:
        quantity = Decimal(str(item_data.get('quantity', 1)))
        unit_price = Decimal(str(item_data['unit_price']))

        line_item = LineItem(
            invoice_id=invoice.id,
            description=item_data['description'],
            quantity=quantity,
            unit_price=unit_price,
            total=quantity * unit_price,
        )
        db.session.add(line_item)

    db.session.flush()

    # Calculate totals
    invoice.calculate_totals()
    db.session.commit()

    logger.info(
        f"Invoice {invoice.invoice_number} generated for client {client_id}: "
        f"${invoice.total}"
    )

    # Publish Kafka event
    publish_event(
        topic=TOPICS['INVOICE_GENERATED'],
        event_type='invoice.generated',
        data={
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'client_id': client_id,
            'total': float(invoice.total),
            'due_date': invoice.due_date.isoformat(),
        },
        key=client_id,
    )

    return invoice


def generate_invoice_for_subscription(subscription_id):
    """Auto-generate invoice from subscription (called by Kafka handler)."""
    subscription = Subscription.query.get(subscription_id)
    if not subscription or not subscription.plan:
        logger.error(f"Subscription {subscription_id} not found or has no plan")
        return None

    plan = subscription.plan
    if float(plan.price) == 0:
        logger.info(f"Skipping invoice for free plan (subscription {subscription_id})")
        return None

    line_items = [{
        'description': f'{plan.name} Plan — {plan.billing_cycle.value.capitalize()} Subscription',
        'quantity': 1,
        'unit_price': float(plan.price),
    }]

    return generate_invoice(
        client_id=subscription.client_id,
        line_items_data=line_items,
        subscription_id=subscription_id,
        notes=f'Auto-generated for {plan.name} plan subscription',
    )


def get_invoices(page=1, per_page=20, status=None, client_id=None):
    """Get paginated invoice list."""
    query = Invoice.query

    if status:
        if isinstance(status, str):
            status = InvoiceStatus(status)
        query = query.filter(Invoice.status == status)

    if client_id:
        query = query.filter(Invoice.client_id == client_id)

    query = query.order_by(Invoice.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        'items': [inv.to_dict() for inv in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    }


def get_invoice(invoice_id):
    """Get a single invoice with all details."""
    return Invoice.query.get_or_404(invoice_id)


def mark_invoice_paid(invoice_id):
    """Mark an invoice as paid."""
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.mark_paid()
    db.session.commit()

    publish_event(
        topic=TOPICS['INVOICE_PAID'],
        event_type='invoice.paid',
        data={
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'client_id': invoice.client_id,
            'total': float(invoice.total),
        },
        key=invoice.client_id,
    )

    logger.info(f"Invoice {invoice.invoice_number} marked as paid")
    return invoice


def mark_invoice_sent(invoice_id):
    """Mark an invoice as sent."""
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.mark_sent()
    db.session.commit()
    return invoice


def get_revenue_summary():
    """Get revenue summary for dashboard."""
    from sqlalchemy import func, extract

    paid_invoices = db.session.query(
        func.sum(Invoice.total),
        func.count(Invoice.id),
    ).filter(Invoice.status == InvoiceStatus.PAID).one()

    pending_amount = db.session.query(
        func.coalesce(func.sum(Invoice.total), 0)
    ).filter(Invoice.status.in_([
        InvoiceStatus.SENT, InvoiceStatus.DRAFT
    ])).scalar()

    overdue_amount = db.session.query(
        func.coalesce(func.sum(Invoice.total), 0)
    ).filter(Invoice.status == InvoiceStatus.OVERDUE).scalar()

    return {
        'total_revenue': float(paid_invoices[0] or 0),
        'total_paid_invoices': paid_invoices[1] or 0,
        'pending_amount': float(pending_amount),
        'overdue_amount': float(overdue_amount),
    }
