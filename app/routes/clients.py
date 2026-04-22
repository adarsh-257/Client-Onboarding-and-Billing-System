"""Client management routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

clients_bp = Blueprint('clients', __name__)


@clients_bp.route('/')
def list_clients():
    """List all clients with search and filters."""
    from app.services.client_service import get_clients, get_all_industries
    from app.models.client import ClientStatus

    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', None)
    search = request.args.get('search', None)
    industry = request.args.get('industry', None)

    clients = get_clients(page=page, per_page=20, status=status, search=search, industry=industry)
    industries = get_all_industries()
    statuses = [s.value for s in ClientStatus]

    # If HTMX request, return only the table partial
    if request.headers.get('HX-Request'):
        return render_template('clients/_table.html', clients=clients)

    return render_template(
        'clients/list.html',
        clients=clients,
        industries=industries,
        statuses=statuses,
        current_status=status,
        current_search=search or '',
        current_industry=industry,
    )


@clients_bp.route('/onboard', methods=['GET', 'POST'])
def onboard():
    """Client onboarding form."""
    if request.method == 'POST':
        from app.services.client_service import onboard_client

        data = {
            'company_name': request.form['company_name'],
            'contact_name': request.form['contact_name'],
            'email': request.form['email'],
            'phone': request.form.get('phone'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'country': request.form.get('country', 'US'),
            'industry': request.form.get('industry'),
            'company_size': request.form.get('company_size'),
            'notes': request.form.get('notes'),
        }

        try:
            client = onboard_client(data)
            flash(f'Client "{client.company_name}" onboarded successfully!', 'success')
            return redirect(url_for('clients.detail', client_id=client.id))
        except Exception as e:
            flash(f'Error onboarding client: {str(e)}', 'error')

    return render_template('clients/onboard.html')


@clients_bp.route('/<int:client_id>')
def detail(client_id):
    """Client detail page."""
    from app.services.client_service import get_client
    from app.services.subscription_service import get_subscriptions
    from app.services.invoice_service import get_invoices
    from app.services.document_service import get_documents

    client = get_client(client_id)
    subscriptions = get_subscriptions(client_id=client_id, per_page=10)
    invoices = get_invoices(client_id=client_id, per_page=10)
    documents = get_documents(client_id=client_id, per_page=10)

    return render_template(
        'clients/detail.html',
        client=client,
        subscriptions=subscriptions,
        invoices=invoices,
        documents=documents,
    )


@clients_bp.route('/<int:client_id>/status', methods=['POST'])
def update_status(client_id):
    """Update client status (HTMX endpoint)."""
    from app.services.client_service import update_client_status

    new_status = request.form.get('status')
    try:
        client = update_client_status(client_id, new_status)
        flash(f'Client status updated to {new_status}', 'success')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('clients.detail', client_id=client_id))


@clients_bp.route('/<int:client_id>/subscribe', methods=['POST'])
def subscribe(client_id):
    """Create subscription for client."""
    from app.services.subscription_service import create_subscription

    plan_id = request.form.get('plan_id', type=int)
    try:
        subscription = create_subscription(client_id, plan_id)
        flash(f'Subscription created successfully!', 'success')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('clients.detail', client_id=client_id))
