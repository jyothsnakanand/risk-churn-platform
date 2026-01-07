"""Secrets management for ML platform.

Supports multiple backends:
- Environment variables (dev)
- AWS Secrets Manager (production)
- HashiCorp Vault (enterprise)
- Kubernetes Secrets (k8s)
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Any

import structlog

logger = structlog.get_logger()


class SecretsBackend(ABC):
    """Abstract base for secrets backends."""

    @abstractmethod
    def get_secret(self, key: str) -> str | None:
        """Get a secret value.

        Args:
            key: Secret key/name

        Returns:
            Secret value or None if not found
        """
        pass

    @abstractmethod
    def get_secret_dict(self, key: str) -> dict[str, Any] | None:
        """Get a secret as dictionary (for JSON secrets).

        Args:
            key: Secret key/name

        Returns:
            Secret dictionary or None if not found
        """
        pass


class EnvironmentSecretsBackend(SecretsBackend):
    """Load secrets from environment variables."""

    def get_secret(self, key: str) -> str | None:
        """Get secret from environment.

        Args:
            key: Environment variable name

        Returns:
            Secret value or None
        """
        value = os.getenv(key)
        if value:
            logger.debug("secret_loaded_from_env", key=key)
        return value

    def get_secret_dict(self, key: str) -> dict[str, Any] | None:
        """Get secret as dictionary from environment.

        Args:
            key: Environment variable name (should contain JSON)

        Returns:
            Secret dictionary or None
        """
        value = self.get_secret(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error("invalid_json_secret", key=key)
                return None
        return None


class AWSSecretsBackend(SecretsBackend):
    """Load secrets from AWS Secrets Manager."""

    def __init__(self, region: str = "us-east-1") -> None:
        """Initialize AWS Secrets Manager backend.

        Args:
            region: AWS region
        """
        self.region = region
        self._client = None

    @property
    def client(self):
        """Lazy-load boto3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("secretsmanager", region_name=self.region)
                logger.info("aws_secrets_manager_initialized", region=self.region)
            except ImportError as err:
                logger.error("boto3_not_installed")
                raise RuntimeError("boto3 required for AWS Secrets Manager") from err
        return self._client

    def get_secret(self, key: str) -> str | None:
        """Get secret from AWS Secrets Manager.

        Args:
            key: Secret name in AWS

        Returns:
            Secret value or None
        """
        try:
            response = self.client.get_secret_value(SecretId=key)
            logger.info("secret_loaded_from_aws", key=key)
            return response.get("SecretString")
        except Exception as e:
            logger.error("aws_secret_fetch_failed", key=key, error=str(e))
            return None

    def get_secret_dict(self, key: str) -> dict[str, Any] | None:
        """Get secret as dictionary from AWS.

        Args:
            key: Secret name

        Returns:
            Secret dictionary or None
        """
        value = self.get_secret(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error("invalid_json_secret_aws", key=key)
                return None
        return None


class VaultSecretsBackend(SecretsBackend):
    """Load secrets from HashiCorp Vault."""

    def __init__(
        self,
        url: str = "http://localhost:8200",
        token: str | None = None,
        mount_point: str = "secret"
    ) -> None:
        """Initialize Vault backend.

        Args:
            url: Vault server URL
            token: Vault token (or from VAULT_TOKEN env)
            mount_point: KV mount point
        """
        self.url = url
        self.token = token or os.getenv("VAULT_TOKEN")
        self.mount_point = mount_point
        self._client = None

    @property
    def client(self):
        """Lazy-load hvac client."""
        if self._client is None:
            try:
                import hvac
                self._client = hvac.Client(url=self.url, token=self.token)
                if not self._client.is_authenticated():
                    raise RuntimeError("Vault authentication failed")
                logger.info("vault_initialized", url=self.url)
            except ImportError as err:
                logger.error("hvac_not_installed")
                raise RuntimeError("hvac required for HashiCorp Vault") from err
        return self._client

    def get_secret(self, key: str) -> str | None:
        """Get secret from Vault.

        Args:
            key: Secret path (e.g., "ml-platform/api-key")

        Returns:
            Secret value or None
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=key, mount_point=self.mount_point
            )
            data = response["data"]["data"]
            logger.info("secret_loaded_from_vault", key=key)
            # If single value, return it; else return JSON
            if len(data) == 1:
                return list(data.values())[0]
            return json.dumps(data)
        except Exception as e:
            logger.error("vault_secret_fetch_failed", key=key, error=str(e))
            return None

    def get_secret_dict(self, key: str) -> dict[str, Any] | None:
        """Get secret as dictionary from Vault.

        Args:
            key: Secret path

        Returns:
            Secret dictionary or None
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=key, mount_point=self.mount_point
            )
            return response["data"]["data"]
        except Exception as e:
            logger.error("vault_secret_dict_fetch_failed", key=key, error=str(e))
            return None


class SecretsManager:
    """Unified secrets manager with multiple backends."""

    def __init__(
        self,
        backend: SecretsBackend | None = None,
        fallback_to_env: bool = True
    ) -> None:
        """Initialize secrets manager.

        Args:
            backend: Primary secrets backend
            fallback_to_env: Fall back to environment variables if secret not found
        """
        self.backend = backend or self._detect_backend()
        self.fallback_to_env = fallback_to_env
        self.env_backend = EnvironmentSecretsBackend()

    def _detect_backend(self) -> SecretsBackend:
        """Auto-detect secrets backend based on environment.

        Returns:
            Appropriate secrets backend
        """
        # Check if running in AWS (EC2, ECS, Lambda)
        if os.getenv("AWS_REGION") or os.path.exists("/var/run/secrets/kubernetes.io"):
            try:
                logger.info("detected_aws_environment")
                return AWSSecretsBackend(region=os.getenv("AWS_REGION", "us-east-1"))
            except Exception as e:
                logger.warning("aws_backend_init_failed", error=str(e))

        # Check if Vault token available
        if os.getenv("VAULT_TOKEN"):
            try:
                logger.info("detected_vault_environment")
                return VaultSecretsBackend()
            except Exception as e:
                logger.warning("vault_backend_init_failed", error=str(e))

        # Default to environment variables
        logger.info("using_environment_variables_backend")
        return EnvironmentSecretsBackend()

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a secret value.

        Args:
            key: Secret key/name
            default: Default value if not found

        Returns:
            Secret value or default
        """
        # Try primary backend
        value = self.backend.get_secret(key)

        # Fallback to environment if enabled
        if value is None and self.fallback_to_env:
            value = self.env_backend.get_secret(key)

        return value or default

    def get_dict(self, key: str, default: dict | None = None) -> dict[str, Any] | None:
        """Get a secret as dictionary.

        Args:
            key: Secret key/name
            default: Default dictionary if not found

        Returns:
            Secret dictionary or default
        """
        # Try primary backend
        value = self.backend.get_secret_dict(key)

        # Fallback to environment if enabled
        if value is None and self.fallback_to_env:
            value = self.env_backend.get_secret_dict(key)

        return value or default

    def require(self, key: str) -> str:
        """Get a required secret (raise if not found).

        Args:
            key: Secret key/name

        Returns:
            Secret value

        Raises:
            RuntimeError: If secret not found
        """
        value = self.get(key)
        if value is None:
            logger.error("required_secret_missing", key=key)
            raise RuntimeError(f"Required secret not found: {key}")
        return value


# Global secrets manager instance
_secrets_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Get global secrets manager instance.

    Returns:
        Secrets manager
    """
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret(key: str, default: str | None = None) -> str | None:
    """Convenience function to get a secret.

    Args:
        key: Secret key/name
        default: Default value

    Returns:
        Secret value or default
    """
    return get_secrets_manager().get(key, default)


def require_secret(key: str) -> str:
    """Convenience function to get a required secret.

    Args:
        key: Secret key/name

    Returns:
        Secret value

    Raises:
        RuntimeError: If secret not found
    """
    return get_secrets_manager().require(key)
