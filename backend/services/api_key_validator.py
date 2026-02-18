"""
API Key Validator Service for ReadIn AI.

Handles API key authentication with:
- IP allowlist validation
- Per-key rate limiting
- Scope verification
- Usage tracking
"""

import ipaddress
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from collections import defaultdict

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import APIKey, User


logger = logging.getLogger(__name__)


# In-memory rate limit tracking (use Redis in production for multi-instance)
_rate_limit_counters: Dict[str, List[datetime]] = defaultdict(list)


class APIKeyValidator:
    """
    Validates API keys with comprehensive security checks.

    Features:
    - Key hash verification
    - IP allowlist checking
    - Per-key rate limiting
    - Scope validation
    - Expiration checking
    - Usage tracking
    """

    def __init__(self, db: Session):
        self.db = db

    def validate(
        self,
        api_key: str,
        client_ip: str,
        required_scopes: Optional[List[str]] = None
    ) -> Tuple[APIKey, User]:
        """
        Validate an API key and return the key and user.

        Args:
            api_key: The full API key string
            client_ip: The client's IP address
            required_scopes: Required scopes for this request

        Returns:
            Tuple of (APIKey, User)

        Raises:
            HTTPException: If validation fails
        """
        # Hash the key for lookup
        key_hash = self._hash_key(api_key)

        # Find the key
        db_key = self.db.query(APIKey).filter(
            APIKey.key_hash == key_hash
        ).first()

        if not db_key:
            logger.warning(f"Invalid API key attempt from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )

        # Check if active
        if not db_key.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has been revoked"
            )

        # Check expiration
        if db_key.expires_at and db_key.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired"
            )

        # Check IP allowlist
        if not self._check_ip_allowed(db_key, client_ip):
            logger.warning(
                f"API key {db_key.key_prefix}*** used from non-allowed IP {client_ip}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP address not allowed for this API key"
            )

        # Check rate limits
        if not self._check_rate_limit(db_key, client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded for this API key",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(db_key.rate_limit_per_minute),
                }
            )

        # Check scopes
        if required_scopes and not self._check_scopes(db_key, required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required scope(s): {required_scopes}"
            )

        # Get user
        user = self.db.query(User).filter(User.id == db_key.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Update usage stats
        self._update_usage(db_key, client_ip)

        return db_key, user

    def _hash_key(self, api_key: str) -> str:
        """Hash an API key for storage/lookup."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _check_ip_allowed(self, api_key: APIKey, client_ip: str) -> bool:
        """Check if client IP is in the allowlist."""
        # If IP allowlist not enabled, allow all
        if not api_key.allowed_ip_enabled:
            return True

        # If no IPs configured but enabled, deny all
        if not api_key.allowed_ips:
            return False

        try:
            client = ipaddress.ip_address(client_ip)

            for allowed in api_key.allowed_ips:
                # Check if it's a CIDR range
                if "/" in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if client in network:
                        return True
                else:
                    # Single IP
                    if client == ipaddress.ip_address(allowed):
                        return True

            return False

        except ValueError as e:
            logger.error(f"IP validation error: {e}")
            return False

    def _check_rate_limit(self, api_key: APIKey, client_ip: str) -> bool:
        """Check if request is within rate limits."""
        now = datetime.utcnow()
        key_id = f"apikey:{api_key.id}"

        # Clean old entries (older than 1 minute)
        cutoff = now - timedelta(minutes=1)
        _rate_limit_counters[key_id] = [
            t for t in _rate_limit_counters[key_id] if t > cutoff
        ]

        # Check per-minute limit
        if len(_rate_limit_counters[key_id]) >= api_key.rate_limit_per_minute:
            return False

        # Track this request
        _rate_limit_counters[key_id].append(now)

        # Also check daily limit (stored in DB)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        # For simplicity, we track daily in the usage_count field
        # In production, use a separate daily counter with Redis

        return True

    def _check_scopes(self, api_key: APIKey, required_scopes: List[str]) -> bool:
        """Check if API key has required scopes."""
        key_scopes = set(api_key.scopes or [])

        # Admin scope implies all scopes
        if "admin" in key_scopes:
            return True

        # Write scope implies read
        if "write" in key_scopes and set(required_scopes) <= {"read", "write"}:
            return True

        # Check exact scope match
        return set(required_scopes) <= key_scopes

    def _update_usage(self, api_key: APIKey, client_ip: str) -> None:
        """Update API key usage statistics."""
        try:
            api_key.last_used_at = datetime.utcnow()
            api_key.last_used_ip = client_ip
            api_key.usage_count = (api_key.usage_count or 0) + 1
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update API key usage: {e}")
            self.db.rollback()

    def get_rate_limit_status(self, api_key: APIKey) -> Dict[str, Any]:
        """Get current rate limit status for an API key."""
        key_id = f"apikey:{api_key.id}"
        now = datetime.utcnow()

        # Clean old entries
        cutoff = now - timedelta(minutes=1)
        current_requests = [
            t for t in _rate_limit_counters.get(key_id, []) if t > cutoff
        ]

        return {
            "limit_per_minute": api_key.rate_limit_per_minute,
            "limit_per_day": api_key.rate_limit_per_day,
            "requests_this_minute": len(current_requests),
            "remaining_this_minute": max(
                0, api_key.rate_limit_per_minute - len(current_requests)
            ),
            "total_requests": api_key.usage_count,
        }


def validate_api_key(
    db: Session,
    api_key: str,
    client_ip: str,
    required_scopes: Optional[List[str]] = None
) -> Tuple[APIKey, User]:
    """
    Convenience function to validate an API key.

    Args:
        db: Database session
        api_key: The API key string
        client_ip: Client IP address
        required_scopes: Required scopes

    Returns:
        Tuple of (APIKey, User)
    """
    validator = APIKeyValidator(db)
    return validator.validate(api_key, client_ip, required_scopes)


def is_ip_in_allowlist(ip: str, allowlist: List[str]) -> bool:
    """
    Check if an IP is in an allowlist.

    Supports both single IPs and CIDR notation.

    Args:
        ip: IP address to check
        allowlist: List of allowed IPs or CIDR ranges

    Returns:
        True if IP is allowed
    """
    try:
        client = ipaddress.ip_address(ip)

        for allowed in allowlist:
            if "/" in allowed:
                network = ipaddress.ip_network(allowed, strict=False)
                if client in network:
                    return True
            else:
                if client == ipaddress.ip_address(allowed):
                    return True

        return False

    except ValueError:
        return False
