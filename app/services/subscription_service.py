"""Subscription service — handles subscription provisioning and management."""
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.subscription import Plan, Subscription, SubscriptionStatus, BillingCycle
from app.models.client import Client
from app.kafka.producer import publish_event
from app.kafka.topics import TOPICS

logger = logging.getLogger(__name__)


def get_or_create_default_plans():
    """Create default subscription plans if they don't exist."""
    default_plans = [
        {
            'name': 'Free',
            'description': 'Basic access for small teams getting started',
            'price': Decimal('0.00'),
            'billing_cycle': BillingCycle.MONTHLY,
            'features': ['5 Users', '1 GB Storage', 'Email Support', 'Basic Analytics'],
            'max_users': 5,
            'max_storage_gb': 1,
        },
        {
            'name': 'Starter',
            'description': 'Essential tools for growing businesses',
            'price': Decimal('29.99'),
            'billing_cycle': BillingCycle.MONTHLY,
            'features': ['25 Users', '10 GB Storage', 'Priority Support', 'Advanced Analytics', 'API Access'],
            'max_users': 25,
            'max_storage_gb': 10,
        },
        {
            'name': 'Professional',
            'description': 'Advanced features for established teams',
            'price': Decimal('99.99'),
            'billing_cycle': BillingCycle.MONTHLY,
            'features': ['100 Users', '100 GB Storage', '24/7 Support', 'Custom Reports', 'API Access', 'SSO', 'Audit Logs'],
            'max_users': 100,
            'max_storage_gb': 100,
        },
        {
            'name': 'Enterprise',
            'description': 'Full platform access for large organizations',
            'price': Decimal('299.99'),
            'billing_cycle': BillingCycle.MONTHLY,
            'features': ['Unlimited Users', '1 TB Storage', 'Dedicated Support', 'Custom Integrations', 'SLA', 'White Labeling', 'Advanced Security'],
            'max_users': 9999,
            'max_storage_gb': 1000,
        },
    ]

    plans = []
    for plan_data in default_plans:
        plan = Plan.query.filter_by(name=plan_data['name']).first()
        if not plan:
            plan = Plan(**plan_data)
            db.session.add(plan)
            logger.info(f"Created plan: {plan_data['name']}")
        plans.append(plan)

    db.session.commit()
    return plans


def create_subscription(client_id, plan_id, auto_renew=True):
    """
    Create a new subscription linking a client to a plan.

    Args:
        client_id: Client ID
        plan_id: Plan ID
        auto_renew: Whether to auto-renew

    Returns:
        Subscription instance
    """
    client = Client.query.get_or_404(client_id)
    plan = Plan.query.get_or_404(plan_id)

    # Check for existing active subscription
    existing = Subscription.query.filter_by(
        client_id=client_id,
        status=SubscriptionStatus.ACTIVE,
    ).first()

    if existing:
        raise ValueError(f"Client {client_id} already has an active subscription (ID: {existing.id})")

    now = datetime.now(timezone.utc)

    # Calculate end date based on billing cycle
    if plan.billing_cycle == BillingCycle.MONTHLY:
        end_date = now + timedelta(days=30)
    elif plan.billing_cycle == BillingCycle.QUARTERLY:
        end_date = now + timedelta(days=90)
    else:  # ANNUAL
        end_date = now + timedelta(days=365)

    subscription = Subscription(
        client_id=client_id,
        plan_id=plan_id,
        status=SubscriptionStatus.ACTIVE,
        start_date=now,
        end_date=end_date,
        auto_renew=auto_renew,
    )

    db.session.add(subscription)
    db.session.commit()

    logger.info(
        f"Subscription created: client={client_id}, plan={plan.name}, "
        f"subscription_id={subscription.id}"
    )

    # Publish Kafka event
    publish_event(
        topic=TOPICS['SUBSCRIPTION_CREATED'],
        event_type='subscription.created',
        data={
            'subscription_id': subscription.id,
            'client_id': client_id,
            'plan_id': plan_id,
            'plan_name': plan.name,
            'price': float(plan.price),
            'billing_cycle': plan.billing_cycle.value,
        },
        key=client_id,
    )

    return subscription


def create_default_subscription(client_id):
    """Create a default (Free plan) subscription for a newly onboarded client."""
    free_plan = Plan.query.filter_by(name='Free').first()
    if not free_plan:
        plans = get_or_create_default_plans()
        free_plan = plans[0]

    return create_subscription(client_id, free_plan.id)


def cancel_subscription(subscription_id, reason=None):
    """Cancel a subscription."""
    subscription = Subscription.query.get_or_404(subscription_id)

    if subscription.status == SubscriptionStatus.CANCELLED:
        raise ValueError("Subscription is already cancelled")

    subscription.cancel(reason)
    db.session.commit()

    logger.info(f"Subscription {subscription_id} cancelled: {reason}")

    publish_event(
        topic=TOPICS['SUBSCRIPTION_CANCELLED'],
        event_type='subscription.cancelled',
        data={
            'subscription_id': subscription_id,
            'client_id': subscription.client_id,
            'reason': reason,
        },
        key=subscription.client_id,
    )

    return subscription


def get_subscriptions(page=1, per_page=20, status=None, client_id=None):
    """Get paginated subscription list."""
    query = Subscription.query

    if status:
        if isinstance(status, str):
            status = SubscriptionStatus(status)
        query = query.filter(Subscription.status == status)

    if client_id:
        query = query.filter(Subscription.client_id == client_id)

    query = query.order_by(Subscription.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        'items': [s.to_dict() for s in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    }


def get_plans():
    """Get all active plans."""
    plans = Plan.query.filter_by(is_active=True).order_by(Plan.price.asc()).all()
    return [p.to_dict() for p in plans]
