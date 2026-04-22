# Client Onboarding and Billing System

A fully-featured, event-driven web application built to streamline client life-cycles, subscriptions, automatic monthly invoice generation, and secure document management. 

This platform leverages modern asynchronous architectures via **Apache Kafka** and powerful deployment stacks on **AWS**, bound together seamlessly by a reactive Server-Side Rendered (SSR) Glassmorphism Web Interface.

## 🚀 Features
- **Client Management Ecosystem**: Track client states from Pending, Active, to Suspended with robust SQL models.
- **Automated Billing Engine**: Define subscription plans and execute automated invoice generation based on customizable monthly billing cycles.
- **Event-Driven Architecture**: Powered by Apache Kafka; decoupled backend micro-services ensure that resource-intensive operations (like document encrypting and generating trial plans) never block the UI.
- **Premium Glassmorphism UI**: High-end CSS Vanilla styling merged with `HTMX` and `Alpine.js` to create fluid, SPA-like experiences without native React/Vue bloat.
- **GraphQL APIs**: Extensible endpoints designed natively with `Ariadne` for direct client data querying and remote API mutations.
- **AWS Infrastructure Ready**: Includes automated deployment scripts utilizing Python `boto3`, executing CloudFormation YAML for quick Docker instances. Security is bolstered by Lambda Error Handlers and AES-256 S3.

## 🛠️ Tech Stack
- **Backend**: Python 3.9, Flask Factory Pattern, Flask-SQLAlchemy (PostgreSQL).
- **Frontend**: Jinja2 Templates, HTMX, Alpine.JS, Vanilla CSS (Glassmorphism).
- **APIs**: GraphQL via Ariadne.
- **Data & Streaming**: PostgreSQL DB, Apache Kafka, Zookeeper.
- **Cloud & Deployment**: AWS EC2, S3, CloudFormation, AWS Lambda, Docker, Docker Compose.

---

## 💻 Local Development Setup

To easily host the entire environment locally, we leverage **Docker** and **Docker-Compose**, stripping away the complexity of managing Kafka pipelines locally.

### 1. Requirements
- Install **Docker** and **Docker Compose**.
- Install **Python 3.9+** (if running headless testing).

### 2. Environment Variables
Duplicate the example environment file and insert your development credentials (specifically if using the AWS Document extensions).
```bash
cp .env.example .env
```

### 3. Spin Up the Platform
Boot the stack. This will provision the PostgreSQL database, Kafka nodes, Web Server, and background Event Listeners simultaneously.
```bash
docker-compose up --build -d
```

### 4. Seed the Database
To verify UI elements and GraphQL boundaries efficiently, you can mock over 500+ real-world simulated client entries, 2000+ files, and 800+ generated invoices by running:
```bash
docker-compose exec web python scripts/seed_data.py
```

*You can now access your dashboard locally at: `http://localhost:5000`*

---

## 🧪 Testing

Testing is implemented rigorously via `pytest`. To run tests locally, utilize isolated environments without affecting the Docker state:
```bash
pip install -r requirements.txt
pytest tests/
```

## ☁️ Deployment (AWS)

Automated provisioning logic to AWS is located in the `/deploy` folder.
*Configure your Local AWS CLI credentials first:*
```bash
aws configure
```
Run the deployment script to dynamically bundle the repository, push to an S3 deployment staging layer, and generate an EC2 Server using the predefined CloudFormation parameters.
```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

## 🛡️ Best Practices & Confidentiality
All `.env` variables, database configuration files, virtual environments, and `.aws` logs have been rigorously `.gitignored`. **Never commit any production access keys directly to this repository.**
