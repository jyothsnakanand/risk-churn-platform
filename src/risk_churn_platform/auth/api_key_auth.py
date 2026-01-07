"""API Key authentication for ML platform."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

import structlog
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

logger = structlog.get_logger()

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKey(BaseModel):
    """API Key model."""

    key_id: str
    key_hash: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    permissions: list[str] = ["predict"]  # predict, admin, monitor
    rate_limit: int = 1000  # requests per hour


class APIKeyManager:
    """Manage API keys for authentication."""

    def __init__(self) -> None:
        """Initialize API key manager."""
        self.keys: Dict[str, APIKey] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Load API keys from configuration."""
        # In production, load from database or secure storage
        # For now, create a default admin key
        default_key = "sk_test_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(default_key.encode()).hexdigest()

        self.keys[key_hash] = APIKey(
            key_id="default",
            key_hash=key_hash,
            name="Default Admin Key",
            created_at=datetime.now(),
            permissions=["predict", "admin", "monitor"],
            rate_limit=10000,
        )

        logger.info("default_api_key_created", key=default_key)
        print(f"\n🔑 Default API Key: {default_key}")
        print("   Save this key securely - it won't be shown again!\n")

    def create_key(
        self,
        name: str,
        permissions: list[str],
        rate_limit: int = 1000,
        expires_in_days: Optional[int] = None,
    ) -> str:
        """Create a new API key.

        Args:
            name: Key name/description
            permissions: List of permissions (predict, admin, monitor)
            rate_limit: Requests per hour
            expires_in_days: Optional expiration in days

        Returns:
            The generated API key (only shown once)
        """
        key = "sk_live_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_id = secrets.token_urlsafe(8)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)

        self.keys[key_hash] = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_at=datetime.now(),
            expires_at=expires_at,
            permissions=permissions,
            rate_limit=rate_limit,
        )

        logger.info("api_key_created", key_id=key_id, name=name)
        return key

    def validate_key(self, api_key: str) -> Optional[APIKey]:
        """Validate an API key.

        Args:
            api_key: The API key to validate

        Returns:
            APIKey object if valid, None otherwise
        """
        if not api_key:
            return None

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_obj = self.keys.get(key_hash)

        if not key_obj:
            logger.warning("invalid_api_key_attempt")
            return None

        if not key_obj.is_active:
            logger.warning("inactive_api_key_used", key_id=key_obj.key_id)
            return None

        if key_obj.expires_at and datetime.now() > key_obj.expires_at:
            logger.warning("expired_api_key_used", key_id=key_obj.key_id)
            return None

        return key_obj

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            key_id: The key ID to revoke

        Returns:
            True if revoked, False if not found
        """
        for key_hash, key_obj in self.keys.items():
            if key_obj.key_id == key_id:
                key_obj.is_active = False
                logger.info("api_key_revoked", key_id=key_id)
                return True
        return False

    def list_keys(self) -> list[Dict]:
        """List all API keys (without the actual key).

        Returns:
            List of key metadata
        """
        return [
            {
                "key_id": key.key_id,
                "name": key.name,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "is_active": key.is_active,
                "permissions": key.permissions,
                "rate_limit": key.rate_limit,
            }
            for key in self.keys.values()
        ]


# Global key manager instance
_key_manager: Optional[APIKeyManager] = None


def get_key_manager() -> APIKeyManager:
    """Get the global API key manager."""
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager


async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> APIKey:
    """Verify API key from request header.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        Validated APIKey object

    Raises:
        HTTPException: If key is invalid or missing
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_manager = get_key_manager()
    key_obj = key_manager.validate_key(api_key)

    if not key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return key_obj


def require_permission(permission: str):
    """Decorator to require specific permission.

    Args:
        permission: Required permission (predict, admin, monitor)

    Returns:
        Dependency function for FastAPI
    """

    async def check_permission(api_key: APIKey = Security(verify_api_key)) -> APIKey:
        if permission not in api_key.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {permission}",
            )
        return api_key

    return check_permission
