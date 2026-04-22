"""Client model for managing onboarded clients."""
import enum
from datetime import datetime, timezone
from app.extensions import db


class ClientStatus(enum.Enum):
    """Client lifecycle statuses."""
    PENDING = 'pending'
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    ARCHIVED = 'archived'


class Client(db.Model):
    """Represents an onboarded client/company."""
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False, index=True)
    contact_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100), default='US')
    industry = db.Column(db.String(100))
    company_size = db.Column(db.String(50))  # e.g., '1-10', '11-50', '51-200', '201-500', '500+'
    status = db.Column(
        db.Enum(ClientStatus),
        default=ClientStatus.PENDING,
        nullable=False,
        index=True
    )
    notes = db.Column(db.Text)
    onboarded_at = db.Column(db.DateTime(timezone=True))
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
    subscriptions = db.relationship('Subscription', backref='client', lazy='dynamic', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='client', lazy='dynamic', cascade='all, delete-orphan')
    documents = db.relationship('Document', backref='client', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Client {self.company_name} ({self.status.value})>'

    def to_dict(self):
        """Serialize client to dictionary."""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'contact_name': self.contact_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'industry': self.industry,
            'company_size': self.company_size,
            'status': self.status.value,
            'notes': self.notes,
            'onboarded_at': self.onboarded_at.isoformat() if self.onboarded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def activate(self):
        """Activate client after onboarding."""
        self.status = ClientStatus.ACTIVE
        self.onboarded_at = datetime.now(timezone.utc)

    def suspend(self):
        """Suspend client account."""
        self.status = ClientStatus.SUSPENDED

    def archive(self):
        """Archive client account."""
        self.status = ClientStatus.ARCHIVED
