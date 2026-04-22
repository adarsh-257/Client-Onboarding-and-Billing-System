"""Invoice routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash

invoices_bp = Blueprint('invoices', __name__)


@invoices_bp.route('/')
def list_invoices():
    """List all invoices."""
    from app.services.invoice_service import get_invoices
    from app.models.invoice import InvoiceStatus

    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', None)
    client_id = request.args.get('client_id', None, type=int)

    invoices = get_invoices(page=page, per_page=20, status=status, client_id=client_id)
    statuses = [s.value for s in InvoiceStatus]

    if request.headers.get('HX-Request'):
        return render_template('invoices/_table.html', invoices=invoices)

    return render_template(
        'invoices/list.html',
        invoices=invoices,
        statuses=statuses,
        current_status=status,
    )


@invoices_bp.route('/<int:invoice_id>')
def detail(invoice_id):
    """Invoice detail page."""
    from app.services.invoice_service import get_invoice
    from app.services.client_service import get_client

    invoice = get_invoice(invoice_id)
    client = get_client(invoice.client_id)

    return render_template('invoices/detail.html', invoice=invoice, client=client)


@invoices_bp.route('/<int:invoice_id>/pay', methods=['POST'])
def mark_paid(invoice_id):
    """Mark invoice as paid."""
    from app.services.invoice_service import mark_invoice_paid

    try:
        invoice = mark_invoice_paid(invoice_id)
        flash(f'Invoice {invoice.invoice_number} marked as paid!', 'success')
    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('invoices.detail', invoice_id=invoice_id))


@invoices_bp.route('/<int:invoice_id>/send', methods=['POST'])
def mark_sent(invoice_id):
    """Mark invoice as sent."""
    from app.services.invoice_service import mark_invoice_sent

    try:
        invoice = mark_invoice_sent(invoice_id)
        flash(f'Invoice {invoice.invoice_number} marked as sent!', 'success')
    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('invoices.detail', invoice_id=invoice_id))


@invoices_bp.route('/generate', methods=['GET', 'POST'])
def generate():
    """Generate a new invoice."""
    from app.services.client_service import get_clients
    from app.services.invoice_service import generate_invoice

    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        line_items = []

        # Parse dynamic line items from form
        descriptions = request.form.getlist('description[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for desc, qty, price in zip(descriptions, quantities, unit_prices):
            if desc and price:
                line_items.append({
                    'description': desc,
                    'quantity': float(qty or 1),
                    'unit_price': float(price),
                })

        if not line_items:
            flash('At least one line item is required', 'error')
            return redirect(url_for('invoices.generate'))

        try:
            invoice = generate_invoice(
                client_id=client_id,
                line_items_data=line_items,
                notes=request.form.get('notes'),
            )
            flash(f'Invoice {invoice.invoice_number} generated!', 'success')
            return redirect(url_for('invoices.detail', invoice_id=invoice.id))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    clients = get_clients(per_page=1000)
    return render_template('invoices/generate.html', clients=clients)
