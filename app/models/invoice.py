"""Invoice and LineItem models."""
import enum
from datetime import datetime, timezone
from app.extensions import db


class InvoiceStatus(enum.Enum):
    """Invoice lifecycle statuses."""
    DRAFT = 'draft'
    SENT = 'sent'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'


class Invoice(db.Model):
    """Represents a billing invoice."""
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), index=True)
    invoice_number = db.Column(db.String(50), nullable=False, unique=True, index=True)
    status = db.Column(
        db.Enum(InvoiceStatus),
        default=InvoiceStatus.DRAFT,
        nullable=False,
        index=True
    )
    subtotal = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    tax_rate = db.Column(db.Numeric(5, 4), default=0.10)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    total = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    due_date = db.Column(db.DateTime(timezone=True), nullable=False)
    paid_at = db.Column(db.DateTime(timezone=True))
    notes = db.Column(db.Text)
    pdf_s3_key = db.Column(db.String(500))
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
    line_items = db.relationship('LineItem', backref='invoice', lazy='select', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Invoice {self.invoice_number} ${self.total} ({self.status.value})>'

    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'subscription_id': self.subscription_id,
            'invoice_number': self.invoice_number,
            'status': self.status.value,
            'subtotal': float(self.subtotal),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'total': float(self.total),
            'currency': self.currency,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'notes': self.notes,
            'line_items': [item.to_dict() for item in self.line_items],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def calculate_totals(self):
        """Recalculate invoice totals from line items."""
        self.subtotal = sum(item.total for item in self.line_items)
        self.tax_amount = self.subtotal * self.tax_rate
        self.total = self.subtotal + self.tax_amount

    def mark_paid(self):
        """Mark invoice as paid."""
        self.status = InvoiceStatus.PAID
        self.paid_at = datetime.now(timezone.utc)

    def mark_sent(self):
        """Mark invoice as sent."""
        self.status = InvoiceStatus.SENT

    def mark_overdue(self):
        """Mark invoice as overdue."""
        self.status = InvoiceStatus.OVERDUE


class LineItem(db.Model):
    """Represents a single line item on an invoice."""
    __tablename__ = 'line_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=1.00, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self):
        return f'<LineItem {self.description} ${self.total}>'

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'description': self.description,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'total': float(self.total),
        }

    def calculate_total(self):
        """Calculate line item total."""
        self.total = self.quantity * self.unit_price
