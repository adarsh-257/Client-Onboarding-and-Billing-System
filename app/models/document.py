"""Document model for tracking files stored in S3."""
import enum
from datetime import datetime, timezone, timedelta
from app.extensions import db


class DocumentType(enum.Enum):
    """Document type categories."""
    CONTRACT = 'contract'
    IDENTITY = 'identity'
    FINANCIAL = 'financial'
    LEGAL = 'legal'
    CORRESPONDENCE = 'correspondence'
    OTHER = 'other'


class Document(db.Model):
    """Represents a document stored in AWS S3."""
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    filename = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(500), nullable=False)
    s3_key = db.Column(db.String(1000), nullable=False, unique=True)
    s3_bucket = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100), default='application/octet-stream')
    size_bytes = db.Column(db.BigInteger, default=0)
    document_type = db.Column(
        db.Enum(DocumentType),
        default=DocumentType.OTHER,
        nullable=False
    )
    encryption_status = db.Column(db.String(50), default='AES256')
    retention_days = db.Column(db.Integer, default=365)
    expires_at = db.Column(db.DateTime(timezone=True))
    checksum = db.Column(db.String(64))
    uploaded_by = db.Column(db.String(255))
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime(timezone=True))
    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self):
        return f'<Document {self.filename} ({self.document_type.value})>'

    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            's3_key': self.s3_key,
            's3_bucket': self.s3_bucket,
            'content_type': self.content_type,
            'size_bytes': self.size_bytes,
            'size_display': self._human_readable_size(),
            'document_type': self.document_type.value,
            'encryption_status': self.encryption_status,
            'retention_days': self.retention_days,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_deleted': self.is_deleted,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

    def set_expiration(self):
        """Set expiration date based on retention period."""
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=self.retention_days)

    def soft_delete(self):
        """Soft delete the document."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def _human_readable_size(self):
        """Convert bytes to human-readable size."""
        size = self.size_bytes or 0
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'
