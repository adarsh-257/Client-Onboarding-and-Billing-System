"""Document management routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
import io

documents_bp = Blueprint('documents', __name__)


@documents_bp.route('/')
def list_documents():
    """List all documents."""
    from app.services.document_service import get_documents
    from app.models.document import DocumentType

    page = request.args.get('page', 1, type=int)
    client_id = request.args.get('client_id', None, type=int)
    doc_type = request.args.get('type', None)

    documents = get_documents(page=page, per_page=20, client_id=client_id, document_type=doc_type)
    doc_types = [t.value for t in DocumentType]

    if request.headers.get('HX-Request'):
        return render_template('documents/_table.html', documents=documents)

    return render_template(
        'documents/list.html',
        documents=documents,
        doc_types=doc_types,
        current_type=doc_type,
    )


@documents_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload a document."""
    from app.services.document_service import upload_document
    from app.services.client_service import get_clients
    from app.models.document import DocumentType

    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        file = request.files.get('file')
        doc_type = request.form.get('document_type', 'other')
        retention = request.form.get('retention_days', 365, type=int)

        if not file or not file.filename:
            flash('Please select a file to upload', 'error')
            return redirect(url_for('documents.upload'))

        try:
            document = upload_document(
                client_id=client_id,
                file_obj=file,
                filename=file.filename,
                document_type=doc_type,
                retention_days=retention,
            )
            flash(f'Document "{file.filename}" uploaded successfully!', 'success')
            return redirect(url_for('documents.list_documents'))
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'error')

    clients = get_clients(per_page=1000)
    doc_types = [t.value for t in DocumentType]
    return render_template('documents/upload.html', clients=clients, doc_types=doc_types)


@documents_bp.route('/<int:document_id>/download')
def download(document_id):
    """Download a document via presigned URL."""
    from app.services.document_service import get_download_url

    try:
        url = get_download_url(document_id)
        return redirect(url)
    except Exception as e:
        flash(f'Download failed: {str(e)}', 'error')
        return redirect(url_for('documents.list_documents'))


@documents_bp.route('/<int:document_id>/delete', methods=['POST'])
def delete(document_id):
    """Delete a document."""
    from app.services.document_service import delete_document

    try:
        delete_document(document_id)
        flash('Document deleted successfully', 'success')
    except Exception as e:
        flash(f'Delete failed: {str(e)}', 'error')

    return redirect(url_for('documents.list_documents'))
