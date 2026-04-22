"""
Seed script — Generates 500+ realistic client records with subscriptions and invoices.
Run: python scripts/seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import random

from faker import Faker

from app import create_app
from app.extensions import db
from app.models.client import Client, ClientStatus
from app.models.subscription import Plan, Subscription, SubscriptionStatus, BillingCycle
from app.models.invoice import Invoice, LineItem, InvoiceStatus
from app.models.document import Document, DocumentType

fake = Faker()


def seed_plans():
    """Create default subscription plans."""
    print("📋 Creating subscription plans...")
    plans_data = [
        {
            'name': 'Free', 'description': 'Basic access for small teams',
            'price': Decimal('0.00'), 'billing_cycle': BillingCycle.MONTHLY,
            'features': ['5 Users', '1 GB Storage', 'Email Support'],
            'max_users': 5, 'max_storage_gb': 1,
        },
        {
            'name': 'Starter', 'description': 'Essential tools for growing businesses',
            'price': Decimal('29.99'), 'billing_cycle': BillingCycle.MONTHLY,
            'features': ['25 Users', '10 GB Storage', 'Priority Support', 'API Access'],
            'max_users': 25, 'max_storage_gb': 10,
        },
        {
            'name': 'Professional', 'description': 'Advanced features for established teams',
            'price': Decimal('99.99'), 'billing_cycle': BillingCycle.MONTHLY,
            'features': ['100 Users', '100 GB Storage', '24/7 Support', 'SSO', 'Audit Logs'],
            'max_users': 100, 'max_storage_gb': 100,
        },
        {
            'name': 'Enterprise', 'description': 'Full platform access for large organizations',
            'price': Decimal('299.99'), 'billing_cycle': BillingCycle.MONTHLY,
            'features': ['Unlimited Users', '1 TB Storage', 'Dedicated Support', 'SLA'],
            'max_users': 9999, 'max_storage_gb': 1000,
        },
    ]

    plans = []
    for pd in plans_data:
        plan = Plan.query.filter_by(name=pd['name']).first()
        if not plan:
            plan = Plan(**pd)
            db.session.add(plan)
        plans.append(plan)

    db.session.commit()
    print(f"  ✅ {len(plans)} plans ready")
    return plans


def seed_clients(count=520):
    """Generate realistic client records."""
    print(f"👥 Generating {count} clients...")

    industries = [
        'Technology', 'Healthcare', 'Finance', 'Education', 'Retail',
        'Manufacturing', 'Consulting', 'Real Estate', 'Media', 'Legal',
        'Logistics', 'Energy', 'Insurance', 'Hospitality', 'Telecom',
    ]

    sizes = ['1-10', '11-50', '51-200', '201-500', '500+']
    statuses = [ClientStatus.ACTIVE] * 8 + [ClientStatus.PENDING, ClientStatus.SUSPENDED]

    clients = []
    for i in range(count):
        status = random.choice(statuses)
        created = fake.date_time_between(start_date='-2y', end_date='now', tzinfo=timezone.utc)

        client = Client(
            company_name=fake.company(),
            contact_name=fake.name(),
            email=fake.unique.email(),
            phone=fake.phone_number(),
            address=fake.street_address(),
            city=fake.city(),
            state=fake.state(),
            country='US',
            industry=random.choice(industries),
            company_size=random.choice(sizes),
            status=status,
            notes=fake.sentence() if random.random() > 0.7 else None,
            onboarded_at=created if status == ClientStatus.ACTIVE else None,
            created_at=created,
            updated_at=created,
        )
        db.session.add(client)
        clients.append(client)

        if (i + 1) % 100 == 0:
            print(f"  ... {i + 1}/{count} clients created")

    db.session.commit()
    print(f"  ✅ {len(clients)} clients created")
    return clients


def seed_subscriptions(clients, plans):
    """Create subscriptions for active clients."""
    print("📋 Creating subscriptions...")

    active_clients = [c for c in clients if c.status == ClientStatus.ACTIVE]
    plan_weights = [0.3, 0.35, 0.25, 0.1]  # Free, Starter, Pro, Enterprise

    subscriptions = []
    for client in active_clients:
        plan = random.choices(plans, weights=plan_weights)[0]
        created = client.created_at or datetime.now(timezone.utc)

        sub = Subscription(
            client_id=client.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            start_date=created,
            end_date=created + timedelta(days=30),
            auto_renew=random.random() > 0.15,
            created_at=created,
            updated_at=created,
        )
        db.session.add(sub)
        subscriptions.append(sub)

    db.session.commit()
    print(f"  ✅ {len(subscriptions)} subscriptions created")
    return subscriptions


def seed_invoices(subscriptions):
    """Generate invoices for paid subscriptions."""
    print("🧾 Generating invoices...")

    invoices = []
    inv_count = 0

    for sub in subscriptions:
        if not sub.plan or float(sub.plan.price) == 0:
            continue

        # Generate 1-6 months of invoices
        num_invoices = random.randint(1, 6)
        for i in range(num_invoices):
            created = sub.start_date + timedelta(days=30 * i)
            status = random.choices(
                [InvoiceStatus.PAID, InvoiceStatus.SENT, InvoiceStatus.DRAFT, InvoiceStatus.OVERDUE],
                weights=[0.6, 0.15, 0.15, 0.1]
            )[0]

            inv_number = f"INV-{created.strftime('%Y%m')}-{fake.hexify(text='^^^^^^^^').upper()}"

            invoice = Invoice(
                client_id=sub.client_id,
                subscription_id=sub.id,
                invoice_number=inv_number,
                status=status,
                subtotal=sub.plan.price,
                tax_rate=Decimal('0.10'),
                tax_amount=sub.plan.price * Decimal('0.10'),
                total=sub.plan.price * Decimal('1.10'),
                due_date=created + timedelta(days=30),
                paid_at=created + timedelta(days=random.randint(5, 25)) if status == InvoiceStatus.PAID else None,
                notes=f'Auto-generated for {sub.plan.name} plan',
                created_at=created,
                updated_at=created,
            )
            db.session.add(invoice)
            db.session.flush()

            # Add line item
            line_item = LineItem(
                invoice_id=invoice.id,
                description=f'{sub.plan.name} Plan — Monthly Subscription',
                quantity=Decimal('1'),
                unit_price=sub.plan.price,
                total=sub.plan.price,
            )
            db.session.add(line_item)

            invoices.append(invoice)
            inv_count += 1

        if inv_count >= 800:
            break

    db.session.commit()
    print(f"  ✅ {len(invoices)} invoices generated")
    return invoices


def seed_documents(clients):
    """Create document metadata entries."""
    print("📁 Creating document records...")

    doc_types = list(DocumentType)
    file_extensions = ['.pdf', '.docx', '.xlsx', '.png', '.jpg']
    content_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
    }

    documents = []
    active_clients = [c for c in clients if c.status == ClientStatus.ACTIVE]

    # Create ~2000 documents across clients
    for i in range(min(2000, len(active_clients) * 5)):
        client = random.choice(active_clients)
        ext = random.choice(file_extensions)
        doc_type = random.choice(doc_types)
        original_name = f"{fake.word()}_{fake.word()}{ext}"
        unique_name = f"{fake.hexify(text='^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')}{ext}"

        doc = Document(
            client_id=client.id,
            filename=unique_name,
            original_filename=original_name,
            s3_key=f"documents/{client.id}/{unique_name}",
            s3_bucket='client-onboarding-docs',
            content_type=content_types[ext],
            size_bytes=random.randint(1024, 10_000_000),
            document_type=doc_type,
            encryption_status='AES256',
            retention_days=random.choice([90, 180, 365, 730]),
            uploaded_at=fake.date_time_between(start_date='-1y', end_date='now', tzinfo=timezone.utc),
        )
        doc.set_expiration()
        db.session.add(doc)
        documents.append(doc)

        if (i + 1) % 500 == 0:
            print(f"  ... {i + 1}/2000 documents created")

    db.session.commit()
    print(f"  ✅ {len(documents)} documents created")
    return documents


def main():
    """Run the full seed process."""
    app = create_app('development')

    with app.app_context():
        print("\n🚀 Starting database seeding...\n")

        # Create all tables first
        db.create_all()

        # Check if already seeded
        try:
            existing = Client.query.count()
        except Exception:
            existing = 0

        if existing > 0:
            print(f"⚠️  Database already has {existing} clients.")
            resp = input("Do you want to reset and re-seed? (y/N): ")
            if resp.lower() != 'y':
                print("Aborted.")
                return

            print("🗑️  Dropping all data...")
            db.drop_all()
            db.create_all()
            print("  ✅ Tables recreated\n")

        plans = seed_plans()
        clients = seed_clients(520)
        subscriptions = seed_subscriptions(clients, plans)
        invoices = seed_invoices(subscriptions)
        documents = seed_documents(clients)

        print(f"\n🎉 Seeding complete!")
        print(f"   • {len(clients)} clients")
        print(f"   • {len(plans)} plans")
        print(f"   • {len(subscriptions)} subscriptions")
        print(f"   • {len(invoices)} invoices")
        print(f"   • {len(documents)} documents")
        print(f"\n👉 Start the app with: python run.py")
        print(f"👉 Open: http://localhost:5000\n")


if __name__ == '__main__':
    main()
