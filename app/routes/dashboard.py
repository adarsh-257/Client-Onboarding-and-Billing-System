"""Dashboard routes."""
from flask import Blueprint, render_template

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    """Main dashboard page."""
    from app.services.client_service import get_dashboard_stats
    from app.services.invoice_service import get_revenue_summary

    try:
        stats = get_dashboard_stats()
        revenue = get_revenue_summary()
    except Exception:
        stats = {
            'total_clients': 0, 'active_clients': 0, 'pending_clients': 0,
            'active_subscriptions': 0, 'total_revenue': 0.0,
            'pending_invoices': 0, 'overdue_invoices': 0, 'total_documents': 0,
            'recent_clients': [],
        }
        revenue = {
            'total_revenue': 0.0, 'total_paid_invoices': 0,
            'pending_amount': 0.0, 'overdue_amount': 0.0,
        }

    return render_template('dashboard.html', stats=stats, revenue=revenue)


@dashboard_bp.route('/system')
def system_monitor():
    """System monitoring page."""
    return render_template('system.html')
