"""Simple tests for secrets management."""

import os

from risk_churn_platform.config.secrets import (
    EnvironmentSecretsBackend,
    SecretsManager,
    get_secret,
)


def test_environment_backend_get_secret() -> None:
    """Test getting secret from environment."""
    backend = EnvironmentSecretsBackend()

    os.environ["TEST_SECRET"] = "test_value"
    value = backend.get_secret("TEST_SECRET")
    assert value == "test_value"
    del os.environ["TEST_SECRET"]


def test_environment_backend_missing_secret() -> None:
    """Test getting non-existent secret."""
    backend = EnvironmentSecretsBackend()

    value = backend.get_secret("NON_EXISTENT_KEY")
    assert value is None


def test_secrets_manager_get() -> None:
    """Test SecretsManager get method."""
    backend = EnvironmentSecretsBackend()
    manager = SecretsManager(backend=backend)

    os.environ["DB_PASSWORD"] = "secret123"
    value = manager.get("DB_PASSWORD")
    assert value == "secret123"
    del os.environ["DB_PASSWORD"]


def test_secrets_manager_get_with_default() -> None:
    """Test getting secret with default value."""
    backend = EnvironmentSecretsBackend()
    manager = SecretsManager(backend=backend)

    value = manager.get("MISSING_KEY", default="default_val")
    assert value == "default_val"


def test_secrets_manager_require_exists() -> None:
    """Test requiring a secret that exists."""
    backend = EnvironmentSecretsBackend()
    manager = SecretsManager(backend=backend)

    os.environ["REQUIRED_KEY"] = "required_value"
    value = manager.require("REQUIRED_KEY")
    assert value == "required_value"
    del os.environ["REQUIRED_KEY"]


def test_get_secret_helper() -> None:
    """Test get_secret helper function."""
    os.environ["HELPER_SECRET"] = "helper_value"
    value = get_secret("HELPER_SECRET")
    assert value == "helper_value"
    del os.environ["HELPER_SECRET"]


def test_get_secret_with_default() -> None:
    """Test get_secret with default."""
    value = get_secret("MISSING", default="fallback")
    assert value == "fallback"
