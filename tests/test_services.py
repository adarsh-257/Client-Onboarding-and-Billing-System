"""Tests for the service layer."""
import pytest
from decimal import Decimal


def test_onboard_client(app, db_session, sample_client_data):
    """Test client onboarding service."""
    with app.app_context():
        from app.services.client_service import onboard_client
        client = onboard_client(sample_client_data)

        assert client.id is not None
        assert client.company_name == 'Test Corp'
        assert client.status.value == 'active'
        assert client.onboarded_at is not None


def test_get_clients_pagination(app, db_session, sample_client_data):
    """Test client listing with pagination."""
    with app.app_context():
        from app.services.client_service import onboard_client, get_clients

        # Create a few clients
        for i in range(5):
            data = sample_client_data.copy()
            data['email'] = f'test{i}@example.com'
            data['company_name'] = f'Test Corp {i}'
            onboard_client(data)

        result = get_clients(page=1, per_page=3)
        assert result['total'] == 5
        assert len(result['items']) == 3
        assert result['has_next'] is True


def test_client_status_transition(app, db_session, sample_client_data):
    """Test valid and invalid status transitions."""
    with app.app_context():
        from app.services.client_service import onboard_client, update_client_status

        client = onboard_client(sample_client_data)
        assert client.status.value == 'active'

        # Valid: active → suspended
        updated = update_client_status(client.id, 'suspended')
        assert updated.status.value == 'suspended'

        # Valid: suspended → active
        updated = update_client_status(client.id, 'active')
        assert updated.status.value == 'active'

        # Invalid: active → pending
        with pytest.raises(ValueError):
            update_client_status(client.id, 'pending')


def test_create_plans(app, db_session):
    """Test default plan creation."""
    with app.app_context():
        from app.services.subscription_service import get_or_create_default_plans
        plans = get_or_create_default_plans()

        assert len(plans) == 4
        assert plans[0].name == 'Free'
        assert plans[0].price == Decimal('0.00')
        assert plans[3].name == 'Enterprise'


def test_create_subscription(app, db_session, sample_client_data):
    """Test subscription creation."""
    with app.app_context():
        from app.services.client_service import onboard_client
        from app.services.subscription_service import create_subscription, get_or_create_default_plans

        client = onboard_client(sample_client_data)
        plans = get_or_create_default_plans()

        sub = create_subscription(client.id, plans[1].id)  # Starter plan
        assert sub.status.value == 'active'
        assert sub.plan.name == 'Starter'


def test_duplicate_subscription_rejected(app, db_session, sample_client_data):
    """Test that duplicate active subscriptions are rejected."""
    with app.app_context():
        from app.services.client_service import onboard_client
        from app.services.subscription_service import create_subscription, get_or_create_default_plans

        client = onboard_client(sample_client_data)
        plans = get_or_create_default_plans()

        create_subscription(client.id, plans[1].id)

        with pytest.raises(ValueError, match="already has an active subscription"):
            create_subscription(client.id, plans[2].id)


def test_generate_invoice(app, db_session, sample_client_data, sample_invoice_data):
    """Test invoice generation."""
    with app.app_context():
        from app.services.client_service import onboard_client
        from app.services.invoice_service import generate_invoice

        client = onboard_client(sample_client_data)

        invoice = generate_invoice(
            client_id=client.id,
            line_items_data=sample_invoice_data,
        )

        assert invoice.id is not None
        assert invoice.invoice_number.startswith('INV-')
        assert invoice.status.value == 'draft'
        assert len(invoice.line_items) == 2
        assert float(invoice.subtotal) == pytest.approx(119.98, abs=0.01)
        assert float(invoice.total) == pytest.approx(131.98, abs=0.01)  # With 10% tax


def test_mark_invoice_paid(app, db_session, sample_client_data, sample_invoice_data):
    """Test marking invoice as paid."""
    with app.app_context():
        from app.services.client_service import onboard_client
        from app.services.invoice_service import generate_invoice, mark_invoice_paid

        client = onboard_client(sample_client_data)
        invoice = generate_invoice(client_id=client.id, line_items_data=sample_invoice_data)

        paid = mark_invoice_paid(invoice.id)
        assert paid.status.value == 'paid'
        assert paid.paid_at is not None


def test_dashboard_stats(app, db_session, sample_client_data):
    """Test dashboard statistics."""
    with app.app_context():
        from app.services.client_service import onboard_client, get_dashboard_stats

        onboard_client(sample_client_data)
        stats = get_dashboard_stats()

        assert stats['total_clients'] >= 1
        assert stats['active_clients'] >= 1
