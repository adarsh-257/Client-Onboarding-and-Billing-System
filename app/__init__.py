"""Flask application factory."""
import os
import logging
from flask import Flask
from flask_cors import CORS

from config import config_by_name
from app.extensions import db, migrate


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    # Register models (import so Alembic can detect them)
    with app.app_context():
        from app.models import client, subscription, invoice, document  # noqa: F401

    # Register blueprints (routes)
    from app.routes.dashboard import dashboard_bp
    from app.routes.clients import clients_bp
    from app.routes.invoices import invoices_bp
    from app.routes.documents import documents_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clients_bp, url_prefix='/clients')
    app.register_blueprint(invoices_bp, url_prefix='/invoices')
    app.register_blueprint(documents_bp, url_prefix='/documents')

    # Register GraphQL endpoint
    from app.graphql import create_graphql_app
    graphql_app = create_graphql_app()

    from ariadne import graphql_sync
    from flask import request, jsonify

    @app.route('/graphql', methods=['GET'])
    def graphql_playground():
        """Serve the GraphQL Playground IDE."""
        from ariadne.explorer import ExplorerGraphiQL
        explorer = ExplorerGraphiQL()
        return explorer.html(None), 200

    @app.route('/graphql', methods=['POST'])
    def graphql_server():
        """Handle GraphQL queries."""
        data = request.get_json()
        success, result = graphql_sync(
            graphql_app,
            data,
            context_value={"request": request, "db": db},
            debug=app.debug,
        )
        status_code = 200 if success else 400
        return jsonify(result), status_code

    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'client-onboarding-system'}, 200

    return app
