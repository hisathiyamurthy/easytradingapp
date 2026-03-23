"""Application configuration without pydantic_settings to avoid recursion issues."""
import os
from functools import lru_cache
from typing import Optional
import logging

logger = logging.getLogger(__name__)

REQUIRED_SECRETS = [
    "SECRET_KEY",
    "ENCRYPTION_KEY",
    "ENCRYPTION_SALT",
    "DATABASE_URL",
    "REDIS_URL",
]

PRODUCTION_REQUIRED = [
    "SECRET_KEY",
    "ENCRYPTION_KEY",
    "ENCRYPTION_SALT",
]


class Settings:
    """Application settings with environment variable support."""
    
    def __init__(self):
        # App
        self.APP_NAME = os.getenv("APP_NAME", "EasyTradingApp")
        self.APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        
        # Security
        self.SECRET_KEY = os.getenv("SECRET_KEY", "")
        self.ALGORITHM = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        self.INACTIVITY_TIMEOUT_MINUTES = int(os.getenv("INACTIVITY_TIMEOUT_MINUTES", "30"))
        self.SESSION_CHECK_INTERVAL_MINUTES = int(os.getenv("SESSION_CHECK_INTERVAL_MINUTES", "5"))
        
        # Database
        self.DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/trading")
        
        # Redis
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # RabbitMQ
        self.RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        
        # Encryption
        self.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
        self.ENCRYPTION_SALT = os.getenv("ENCRYPTION_SALT", "")
        
        # Rate Limiting
        self.RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        
        # Password Reset
        self.PASSWORD_RESET_TOKEN_EXPIRE_HOURS = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "24"))
        
        # Risk Limits
        self.DEFAULT_DAILY_LOSS_LIMIT = float(os.getenv("DEFAULT_DAILY_LOSS_LIMIT", "1000.0"))
        self.DEFAULT_MAX_POSITION_SIZE = float(os.getenv("DEFAULT_MAX_POSITION_SIZE", "10000.0"))
        self.DEFAULT_MAX_ORDERS_PER_MINUTE = int(os.getenv("DEFAULT_MAX_ORDERS_PER_MINUTE", "10"))
        
        # Broker
        self.BROKER_API_URL = os.getenv("BROKER_API_URL", "https://api.broker.com")
        
        # AWS
        self.AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
        self.AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.AWS_SECRETS_MANAGER_ENABLED = os.getenv("AWS_SECRETS_MANAGER_ENABLED", "false").lower() == "true"
        self.AWS_SECRETS_MANAGER_NAME = os.getenv("AWS_SECRETS_MANAGER_NAME", "")
        
        # OAuth2
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
        
        # Email
        self.SMTP_HOST = os.getenv("SMTP_HOST", "")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER = os.getenv("SMTP_USER", "")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        self.EMAIL_FROM = os.getenv("EMAIL_FROM", "")
        self.SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
        
        # Admin Account
        self.ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
        self.ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


def validate_environment() -> list[str]:
    """Validate that required environment variables are set."""
    settings = Settings()  # Direct instantiation to avoid recursion
    missing = []
    
    check_list = PRODUCTION_REQUIRED if settings.ENVIRONMENT == "production" else REQUIRED_SECRETS
    
    for secret in check_list:
        value = getattr(settings, secret, None)
        if not value or value == "":
            missing.append(secret)
    
    return missing


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    
    if settings.ENVIRONMENT not in ["development", "staging", "production"]:
        logger.warning(f"Unknown ENVIRONMENT: {settings.ENVIRONMENT}, defaulting to development")
        settings.ENVIRONMENT = "development"
    
    missing_secrets = validate_environment()
    if missing_secrets:
        if settings.ENVIRONMENT == "production":
            raise ValueError(
                f"CRITICAL: Missing required secrets for production: {missing_secrets}. "
                f"Set these environment variables before starting the application."
            )
        else:
            logger.warning(
                f"Missing secrets (development mode): {missing_secrets}. "
                f"Some features may not work correctly."
            )
    
    if settings.ENVIRONMENT == "production":
        if settings.DEBUG:
            logger.warning("DEBUG mode is enabled in production - this is a security risk")
        
        if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        
        if not settings.ENCRYPTION_KEY or len(settings.ENCRYPTION_KEY) < 32:
            raise ValueError("ENCRYPTION_KEY must be at least 32 characters in production")
    
    return settings


class SecretsManager:
    """AWS Secrets Manager integration for secure secret storage."""
    
    def __init__(self):
        self._secrets = {}
        self._client = None
    
    async def load_secrets(self) -> bool:
        """Load secrets from AWS Secrets Manager."""
        settings = get_settings()
        
        if not settings.AWS_SECRETS_MANAGER_ENABLED:
            return False
        
        try:
            import boto3
            client = boto3.client(
                'secretsmanager',
                region_name=settings.AWS_REGION,
            )
            
            response = client.get_secret_value(
                SecretId=settings.AWS_SECRETS_MANAGER_NAME
            )
            
            import json
            self._secrets = json.loads(response['SecretString'])
            logger.info(f"Loaded secrets from AWS Secrets Manager: {settings.AWS_SECRETS_MANAGER_NAME}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load secrets from AWS Secrets Manager: {e}")
            return False
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret value."""
        if key in self._secrets:
            return self._secrets[key]
        
        settings = get_settings()
        
        env_key = key.upper()
        return getattr(settings, env_key, default)


_secrets_manager = None


def get_secrets_manager() -> SecretsManager:
    """Get secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
