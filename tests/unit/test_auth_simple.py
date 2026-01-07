"""Simple tests for authentication module."""

import hashlib
import pytest
from datetime import datetime, timedelta

from risk_churn_platform.auth.api_key_auth import (
    APIKey,
    APIKeyManager,
    get_key_manager,
)


def test_api_key_manager_create_key() -> None:
    """Test creating an API key."""
    manager = APIKeyManager()

    key = manager.create_key(
        name="Test Key",
        permissions=["predict"],
        rate_limit=1000
    )

    assert key.startswith("sk_live_")
    assert len(key) > 20


def test_api_key_manager_validate_key() -> None:
    """Test validating an API key."""
    manager = APIKeyManager()

    key = manager.create_key(name="Valid Key", permissions=["predict"])

    api_key = manager.validate_key(key)
    assert api_key is not None
    assert api_key.name == "Valid Key"
    assert "predict" in api_key.permissions


def test_api_key_manager_invalid_key() -> None:
    """Test validating an invalid key."""
    manager = APIKeyManager()

    api_key = manager.validate_key("sk_live_invalid_key_12345")
    assert api_key is None


def test_api_key_manager_revoke_key() -> None:
    """Test revoking an API key."""
    manager = APIKeyManager()

    key = manager.create_key(name="Revoked Key", permissions=["predict"])
    api_key = manager.validate_key(key)
    assert api_key is not None
    key_id = api_key.key_id

    result = manager.revoke_key(key_id)
    assert result is True

    api_key_after = manager.validate_key(key)
    assert api_key_after is None


def test_api_key_manager_list_keys() -> None:
    """Test listing API keys."""
    manager = APIKeyManager()

    manager.create_key(name="Key 1", permissions=["predict"])
    manager.create_key(name="Key 2", permissions=["admin"])

    keys = manager.list_keys()
    assert len(keys) >= 2


def test_get_key_manager() -> None:
    """Test getting singleton key manager."""
    manager1 = get_key_manager()
    manager2 = get_key_manager()

    assert manager1 is manager2


def test_api_key_manager_permissions() -> None:
    """Test API key with different permissions."""
    manager = APIKeyManager()

    key = manager.create_key(name="Admin Key", permissions=["predict", "admin", "monitor"], rate_limit=5000)

    api_key = manager.validate_key(key)
    assert api_key is not None
    assert "predict" in api_key.permissions
    assert "admin" in api_key.permissions
    assert "monitor" in api_key.permissions
    assert api_key.rate_limit == 5000
