"""Tests for GraphQL API endpoints."""
import json
import pytest


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'


def test_graphql_playground_accessible(client):
    """Test GraphQL playground is accessible."""
    response = client.get('/graphql')
    assert response.status_code == 200


def test_graphql_dashboard_stats(client, app, db_session):
    """Test dashboardStats query."""
    with app.app_context():
        query = '''
        query {
            dashboardStats {
                totalClients
                activeClients
                pendingClients
                activeSubscriptions
                totalRevenue
                pendingInvoices
                overdueInvoices
                totalDocuments
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        if 'errors' in data:
            print("GRAPHQL ERRORS:", data['errors'])
        assert 'data' in data
        stats = data['data']['dashboardStats']
        assert stats['totalClients'] >= 0


def test_graphql_clients_query(client, app, db_session):
    """Test clients query."""
    with app.app_context():
        query = '''
        query {
            clients(page: 1, perPage: 10) {
                items {
                    id
                    companyName
                    email
                    status
                }
                total
                pages
                currentPage
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'items' in data['data']['clients']


def test_graphql_onboard_client_mutation(client, app, db_session):
    """Test onboardClient mutation."""
    with app.app_context():
        mutation = '''
        mutation {
            onboardClient(input: {
                companyName: "GraphQL Test Corp"
                contactName: "Jane Smith"
                email: "jane@graphqltest.com"
                industry: "Technology"
            }) {
                id
                companyName
                email
                status
            }
        }
        '''
        response = client.post(
            '/graphql',
            data=json.dumps({'query': mutation}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        result = data['data']['onboardClient']
        assert result['companyName'] == 'GraphQL Test Corp'
        assert result['status'] == 'ACTIVE'


def test_graphql_plans_query(client, app, db_session):
    """Test plans query."""
    with app.app_context():
        # First ensure plans exist
        from app.services.subscription_service import get_or_create_default_plans
        get_or_create_default_plans()

        query = '{ plans { id name price } }'
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        plans = data['data']['plans']
        assert len(plans) >= 4


def test_graphql_industries_query(client, app, db_session):
    """Test industries query."""
    with app.app_context():
        query = '{ industries }'
        response = client.post(
            '/graphql',
            data=json.dumps({'query': query}),
            content_type='application/json',
        )
        assert response.status_code == 200
