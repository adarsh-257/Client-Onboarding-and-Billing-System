"""GraphQL query resolvers."""
from ariadne import QueryType

query = QueryType()


@query.field("clients")
def resolve_clients(_, info, page=1, perPage=20, status=None, search=None, industry=None):
    """Resolve paginated client list with filters."""
    from app.services.client_service import get_clients

    return get_clients(
        page=page,
        per_page=perPage,
        status=status,
        search=search,
        industry=industry,
    )


@query.field("client")
def resolve_client(_, info, id):
    """Resolve a single client by ID."""
    from app.services.client_service import get_client
    client = get_client(id)
    return client.to_dict() if client else None


@query.field("plans")
def resolve_plans(_, info):
    """Resolve all active subscription plans."""
    from app.services.subscription_service import get_plans
    return get_plans()


@query.field("subscriptions")
def resolve_subscriptions(_, info, page=1, perPage=20, status=None, clientId=None):
    """Resolve paginated subscriptions."""
    from app.services.subscription_service import get_subscriptions
    return get_subscriptions(
        page=page,
        per_page=perPage,
        status=status,
        client_id=clientId,
    )


@query.field("invoices")
def resolve_invoices(_, info, page=1, perPage=20, status=None, clientId=None):
    """Resolve paginated invoices."""
    from app.services.invoice_service import get_invoices
    return get_invoices(
        page=page,
        per_page=perPage,
        status=status,
        client_id=clientId,
    )


@query.field("invoice")
def resolve_invoice(_, info, id):
    """Resolve a single invoice."""
    from app.services.invoice_service import get_invoice
    invoice = get_invoice(id)
    return invoice.to_dict() if invoice else None


@query.field("documents")
def resolve_documents(_, info, page=1, perPage=20, clientId=None, documentType=None):
    """Resolve paginated documents."""
    from app.services.document_service import get_documents
    return get_documents(
        page=page,
        per_page=perPage,
        client_id=clientId,
        document_type=documentType,
    )


@query.field("dashboardStats")
def resolve_dashboard_stats(_, info):
    """Resolve dashboard statistics."""
    from app.services.client_service import get_dashboard_stats
    return get_dashboard_stats()


@query.field("revenueSummary")
def resolve_revenue_summary(_, info):
    """Resolve revenue summary."""
    from app.services.invoice_service import get_revenue_summary
    return get_revenue_summary()


@query.field("industries")
def resolve_industries(_, info):
    """Resolve list of unique industries."""
    from app.services.client_service import get_all_industries
    return get_all_industries()
