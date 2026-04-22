"""GraphQL schema assembly using Ariadne."""
from ariadne import (
    make_executable_schema,
    load_schema_from_path,
    QueryType,
    MutationType,
    EnumType,
    snake_case_fallback_resolvers,
)
import os

from app.graphql.queries import query
from app.graphql.mutations import mutation


# Enum type bindings
client_status_enum = EnumType("ClientStatus", {
    "PENDING": "pending",
    "ACTIVE": "active",
    "SUSPENDED": "suspended",
    "ARCHIVED": "archived",
})

subscription_status_enum = EnumType("SubscriptionStatus", {
    "TRIAL": "trial",
    "ACTIVE": "active",
    "PAST_DUE": "past_due",
    "CANCELLED": "cancelled",
    "EXPIRED": "expired",
})

invoice_status_enum = EnumType("InvoiceStatus", {
    "DRAFT": "draft",
    "SENT": "sent",
    "PAID": "paid",
    "OVERDUE": "overdue",
    "CANCELLED": "cancelled",
    "REFUNDED": "refunded",
})

billing_cycle_enum = EnumType("BillingCycle", {
    "MONTHLY": "monthly",
    "QUARTERLY": "quarterly",
    "ANNUAL": "annual",
})

document_type_enum = EnumType("DocumentType", {
    "CONTRACT": "contract",
    "IDENTITY": "identity",
    "FINANCIAL": "financial",
    "LEGAL": "legal",
    "CORRESPONDENCE": "correspondence",
    "OTHER": "other",
})


def create_graphql_app():
    """Create the executable GraphQL schema."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.graphql')
    type_defs = load_schema_from_path(schema_path)

    schema = make_executable_schema(
        type_defs,
        query,
        mutation,
        client_status_enum,
        subscription_status_enum,
        invoice_status_enum,
        billing_cycle_enum,
        document_type_enum,
        snake_case_fallback_resolvers,
    )

    return schema

