"""Application configuration classes."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://onboarding_user:onboarding_pass@localhost:5432/onboarding_db'
    )

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'onboarding-system')

    # AWS
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

    # S3
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'client-onboarding-docs')
    S3_ENCRYPTION = os.getenv('S3_ENCRYPTION', 'AES256')

    # SES
    SES_SENDER_EMAIL = os.getenv('SES_SENDER_EMAIL', 'noreply@example.com')

    # App
    ITEMS_PER_PAGE = int(os.getenv('ITEMS_PER_PAGE', 20))
    INVOICE_TAX_RATE = float(os.getenv('INVOICE_TAX_RATE', 0.10))
    DOCUMENT_RETENTION_DAYS = int(os.getenv('DOCUMENT_RETENTION_DAYS', 365))


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
