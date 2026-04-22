"""Subscription and Plan models."""
import enum
from datetime import datetime, timezone
from app.extensions import db


class BillingCycle(enum.Enum):
    """Billing cycle options."""
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    ANNUAL = 'annual'


class SubscriptionStatus(enum.Enum):
    """Subscription lifecycle statuses."""
    TRIAL = 'trial'
    ACTIVE = 'active'
    PAST_DUE = 'past_due'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'


class Plan(db.Model):
    """Represents a subscription plan/tier."""
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    billing_cycle = db.Column(
        db.Enum(BillingCycle),
        default=BillingCycle.MONTHLY,
        nullable=False
    )
    features = db.Column(db.JSON, default=list)
    max_users = db.Column(db.Integer, default=1)
    max_storage_gb = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    subscriptions = db.relationship('Subscription', backref='plan', lazy='dynamic')

    def __repr__(self):
        return f'<Plan {self.name} ${self.price}/{self.billing_cycle.value}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'billing_cycle': self.billing_cycle.value,
            'features': self.features,
            'max_users': self.max_users,
            'max_storage_gb': self.max_storage_gb,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Subscription(db.Model):
    """Represents a client's active subscription to a plan."""
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False, index=True)
    status = db.Column(
        db.Enum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
        index=True
    )
    start_date = db.Column(db.DateTime(timezone=True), nullable=False)
    end_date = db.Column(db.DateTime(timezone=True))
    auto_renew = db.Column(db.Boolean, default=True)
    cancelled_at = db.Column(db.DateTime(timezone=True))
    cancellation_reason = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    invoices = db.relationship('Invoice', backref='subscription', lazy='dynamic')

    def __repr__(self):
        return f'<Subscription client={self.client_id} plan={self.plan_id} ({self.status.value})>'

    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'plan_id': self.plan_id,
            'plan': self.plan.to_dict() if self.plan else None,
            'status': self.status.value,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'auto_renew': self.auto_renew,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'cancellation_reason': self.cancellation_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def cancel(self, reason=None):
        """Cancel this subscription."""
        self.status = SubscriptionStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)
        self.cancellation_reason = reason
        self.auto_renew = False
