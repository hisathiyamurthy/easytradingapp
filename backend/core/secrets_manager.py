"""AWS Secrets Manager integration for secure secret storage."""
import json
import logging
from typing import Optional, Any
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class SecretsManager:
    """AWS Secrets Manager client for secure secret storage."""

    def __init__(self, region_name: str = "us-east-1"):
        self.region_name = region_name
        self.client = None
        if self._is_configured():
            self.client = boto3.client(
                "secretsmanager",
                region_name=region_name,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID if hasattr(settings, 'AWS_ACCESS_KEY_ID') else None,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY if hasattr(settings, 'AWS_SECRET_ACCESS_KEY') else None,
            )

    def _is_configured(self) -> bool:
        """Check if AWS is configured."""
        return hasattr(settings, 'AWS_ACCESS_KEY_ID') and settings.AWS_ACCESS_KEY_ID

    def get_secret(self, secret_name: str) -> Optional[dict]:
        """Retrieve a secret from AWS Secrets Manager."""
        if not self.client:
            logger.warning("AWS Secrets Manager not configured, using fallback")
            return None

        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret = response["SecretString"]
            return json.loads(secret)
        except ClientError as e:
            logger.error(f"Error retrieving secret {secret_name}: {e}")
            return None
        except json.JSONDecodeError:
            return {"value": secret}

    def put_secret(self, secret_name: str, secret_value: dict) -> bool:
        """Store a secret in AWS Secrets Manager."""
        if not self.client:
            logger.warning("AWS Secrets Manager not configured")
            return False

        try:
            self.client.put_secret_value(
                SecretId=secret_name,
                SecretString=json.dumps(secret_value),
            )
            return True
        except ClientError as e:
            logger.error(f"Error storing secret {secret_name}: {e}")
            return False

    def delete_secret(self, secret_name: str) -> bool:
        """Delete a secret from AWS Secrets Manager."""
        if not self.client:
            return False

        try:
            self.client.delete_secret(
                SecretId=secret_name,
                ForceDeleteWithoutRecovery=True,
            )
            return True
        except ClientError as e:
            logger.error(f"Error deleting secret {secret_name}: {e}")
            return False

    def list_secrets(self) -> list:
        """List all secrets in AWS Secrets Manager."""
        if not self.client:
            return []

        try:
            response = self.client.list_secrets()
            return response.get("SecretList", [])
        except ClientError as e:
            logger.error(f"Error listing secrets: {e}")
            return []


class SecretsManagerMixin:
    """Mixin class to provide secrets management capabilities."""

    _secrets_cache: dict = {}
    _cache_ttl: int = 300

    @property
    def secrets(self) -> SecretsManager:
        """Get secrets manager instance."""
        if not hasattr(self, "_secrets_manager"):
            setattr(self, "_secrets_manager", SecretsManager())
        return getattr(self, "_secrets_manager")

    def get_config_secret(self, key: str, default: Any = None) -> Any:
        """Get a configuration secret with caching."""
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        secret_name = f"{settings.APP_NAME}/{key}"
        secret = self.secrets.get_secret(secret_name)

        if secret:
            self._secrets_cache[key] = secret
            return secret.get("value", default)

        return default


def get_secret(secret_name: str) -> Optional[dict]:
    """Standalone function to get a secret."""
    manager = SecretsManager()
    return manager.get_secret(secret_name)


def put_secret(secret_name: str, secret_value: dict) -> bool:
    """Standalone function to store a secret."""
    manager = SecretsManager()
    return manager.put_secret(secret_name, secret_value)
