"""Document service — handles file upload to S3, metadata tracking, and lifecycle management."""
import os
import logging
import uuid
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models.document import Document, DocumentType
from app.aws.s3_client import s3_client
from app.kafka.producer import publish_event
from app.kafka.topics import TOPICS

logger = logging.getLogger(__name__)


def upload_document(client_id, file_obj, filename, document_type='other',
                    retention_days=365, uploaded_by=None):
    """
    Upload a document to S3 and track metadata.

    Args:
        client_id: Client ID
        file_obj: File-like object
        filename: Original filename
        document_type: Type of document
        retention_days: Days to retain before auto-delete
        uploaded_by: Who uploaded the file

    Returns:
        Document instance
    """
    from app.models.client import Client
    client = Client.query.get_or_404(client_id)

    # Generate unique S3 key
    ext = os.path.splitext(filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    s3_key = f"documents/{client_id}/{unique_name}"

    # Detect content type
    content_type = _detect_content_type(filename)

    # Upload to S3
    upload_result = s3_client.upload_file(
        file_obj=file_obj,
        s3_key=s3_key,
        content_type=content_type,
        metadata={
            'client_id': str(client_id),
            'original_filename': filename,
            'document_type': document_type,
        },
    )

    if not upload_result:
        raise RuntimeError(f"Failed to upload '{filename}' to S3")

    # Parse document type
    if isinstance(document_type, str):
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            doc_type = DocumentType.OTHER
    else:
        doc_type = document_type

    # Create metadata record
    document = Document(
        client_id=client_id,
        filename=unique_name,
        original_filename=filename,
        s3_key=upload_result['s3_key'],
        s3_bucket=upload_result['s3_bucket'],
        content_type=content_type,
        size_bytes=upload_result.get('size_bytes', 0),
        document_type=doc_type,
        encryption_status=upload_result.get('encryption', 'AES256'),
        retention_days=retention_days,
        checksum=upload_result.get('checksum'),
        uploaded_by=uploaded_by,
    )
    document.set_expiration()

    db.session.add(document)
    db.session.commit()

    logger.info(f"Document uploaded: {filename} → {s3_key} (client {client_id})")

    # Publish Kafka event
    publish_event(
        topic=TOPICS['DOCUMENT_UPLOADED'],
        event_type='document.uploaded',
        data={
            'document_id': document.id,
            'client_id': client_id,
            'filename': filename,
            's3_key': s3_key,
            'size_bytes': document.size_bytes,
        },
        key=client_id,
    )

    return document


def get_documents(page=1, per_page=20, client_id=None, document_type=None):
    """Get paginated document list."""
    query = Document.query.filter(Document.is_deleted == False)

    if client_id:
        query = query.filter(Document.client_id == client_id)

    if document_type:
        if isinstance(document_type, str):
            document_type = DocumentType(document_type)
        query = query.filter(Document.document_type == document_type)

    query = query.order_by(Document.uploaded_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        'items': [d.to_dict() for d in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    }


def get_document(document_id):
    """Get a single document."""
    return Document.query.get_or_404(document_id)


def get_download_url(document_id, expiration=900):
    """Generate a presigned download URL for a document."""
    document = Document.query.get_or_404(document_id)

    if document.is_deleted:
        raise ValueError("Document has been deleted")

    url = s3_client.generate_presigned_url(document.s3_key, expiration=expiration)
    if not url:
        raise RuntimeError("Failed to generate download URL")

    return url


def delete_document(document_id):
    """Soft-delete a document (mark as deleted, keep S3 object for retention)."""
    document = Document.query.get_or_404(document_id)
    document.soft_delete()
    db.session.commit()

    publish_event(
        topic=TOPICS['DOCUMENT_DELETED'],
        event_type='document.deleted',
        data={
            'document_id': document.id,
            'client_id': document.client_id,
            's3_key': document.s3_key,
        },
        key=document.client_id,
    )

    logger.info(f"Document {document_id} soft-deleted")
    return document


def purge_expired_documents():
    """
    Permanently delete documents past their retention period.
    Called by a scheduled job.
    """
    now = datetime.now(timezone.utc)
    expired = Document.query.filter(
        Document.expires_at <= now,
        Document.is_deleted == False,
    ).all()

    deleted_count = 0
    for doc in expired:
        # Delete from S3
        s3_client.delete_file(doc.s3_key)
        doc.soft_delete()
        deleted_count += 1

    db.session.commit()
    logger.info(f"Purged {deleted_count} expired documents")
    return deleted_count


def _detect_content_type(filename):
    """Detect MIME type from filename extension."""
    ext = os.path.splitext(filename)[1].lower()
    content_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.csv': 'text/csv',
        '.txt': 'text/plain',
        '.zip': 'application/zip',
    }
    return content_types.get(ext, 'application/octet-stream')
