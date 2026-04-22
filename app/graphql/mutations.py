"""GraphQL mutation resolvers."""
from ariadne import MutationType

mutation = MutationType()


def _snake_case(data):
    """Convert camelCase input keys to snake_case."""
    mapping = {
        'companyName': 'company_name',
        'contactName': 'contact_name',
        'companySize': 'company_size',
    }
    return {mapping.get(k, k): v for k, v in data.items()}


@mutation.field("onboardClient")
def resolve_onboard_client(_, info, input):
    """Onboard a new client."""
    from app.services.client_service import onboard_client
    data = _snake_case(input)
    client = onboard_client(data)
    return client.to_dict()


@mutation.field("updateClient")
def resolve_update_client(_, info, id, input):
    """Update client details."""
    from app.services.client_service import update_client
    data = _snake_case(input)
    client = update_client(id, data)
    return client.to_dict()


@mutation.field("updateClientStatus")
def resolve_update_client_status(_, info, id, status):
    """Update client status."""
    from app.services.client_service import update_client_status
    client = update_client_status(id, status)
    return client.to_dict()


@mutation.field("createSubscription")
def resolve_create_subscription(_, info, input):
    """Create a new subscription."""
    from app.services.subscription_service import create_subscription
    subscription = create_subscription(
        client_id=input['clientId'],
        plan_id=input['planId'],
        auto_renew=input.get('autoRenew', True),
    )
    return subscription.to_dict()


@mutation.field("cancelSubscription")
def resolve_cancel_subscription(_, info, id, reason=None):
    """Cancel a subscription."""
    from app.services.subscription_service import cancel_subscription
    subscription = cancel_subscription(id, reason)
    return subscription.to_dict()


@mutation.field("generateInvoice")
def resolve_generate_invoice(_, info, input):
    """Generate a new invoice."""
    from app.services.invoice_service import generate_invoice

    line_items = []
    for item in input['lineItems']:
        line_items.append({
            'description': item['description'],
            'quantity': item.get('quantity', 1),
            'unit_price': item['unitPrice'],
        })

    invoice = generate_invoice(
        client_id=input['clientId'],
        line_items_data=line_items,
        due_days=input.get('dueDays', 30),
        notes=input.get('notes'),
        subscription_id=input.get('subscriptionId'),
    )
    return invoice.to_dict()


@mutation.field("markInvoicePaid")
def resolve_mark_invoice_paid(_, info, id):
    """Mark an invoice as paid."""
    from app.services.invoice_service import mark_invoice_paid
    invoice = mark_invoice_paid(id)
    return invoice.to_dict()


@mutation.field("markInvoiceSent")
def resolve_mark_invoice_sent(_, info, id):
    """Mark an invoice as sent."""
    from app.services.invoice_service import mark_invoice_sent
    invoice = mark_invoice_sent(id)
    return invoice.to_dict()


@mutation.field("deleteDocument")
def resolve_delete_document(_, info, id):
    """Delete a document."""
    from app.services.document_service import delete_document
    document = delete_document(id)
    return document.to_dict()
