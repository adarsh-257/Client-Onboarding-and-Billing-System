"""Pytest fixtures for the test suite."""
import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app('testing')
    return app


@pytest.fixture(scope='function', autouse=True)
def db_session(app):
    """Create a clean database session for each test."""
    with app.app_context():
        _db.create_all()
        yield _db.session
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def sample_client_data():
    """Sample client data for testing."""
    return {
        'company_name': 'Test Corp',
        'contact_name': 'John Doe',
        'email': 'john@testcorp.com',
        'phone': '+1-555-0100',
        'address': '123 Test St',
        'city': 'San Francisco',
        'state': 'California',
        'country': 'US',
        'industry': 'Technology',
        'company_size': '51-200',
    }


@pytest.fixture
def sample_invoice_data():
    """Sample invoice line items for testing."""
    return [
        {
            'description': 'Professional Plan - Monthly',
            'quantity': 1,
            'unit_price': 99.99,
        },
        {
            'description': 'Additional Storage (50 GB)',
            'quantity': 1,
            'unit_price': 19.99,
        },
    ]
