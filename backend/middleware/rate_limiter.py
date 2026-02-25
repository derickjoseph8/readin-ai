"""
Rate limiting middleware using SlowAPI with Redis support.

IMPORTANT: Redis is REQUIRED for production deployments!
============================================================
In-memory rate limiting is NOT suitable for production because:
- Rate limits are not shared across multiple application instances
- Memory usage grows unbounded over time
- State is lost on application restart

For production, configure REDIS_URL environment variable to point to a Redis instance.
Example: REDIS_URL=redis://localhost:6379/0

The rate limiter will fall back to in-memory storage if Redis is unavailable,
but this should only be used for development/testing.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from typing import Optional, Callable
import logging

from config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_LOGIN,
    RATE_LIMIT_REGISTER,
    RATE_LIMIT_AI,
    RATE_LIMIT_DEFAULT,
    REDIS_URL,
    IS_PRODUCTION,
)

logger = logging.getLogger(__name__)


def get_user_identifier(request: Request) -> str:
    """
    Get rate limit key based on user or IP.

    Uses authenticated user ID if available, otherwise falls back to IP.
    This allows more granular rate limiting for authenticated users.
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # Fall back to IP address
    return get_remote_address(request)


def get_subscription_aware_limit(request: Request) -> str:
    """
    Return different rate limits based on subscription status.

    Premium users get higher limits.
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "subscription_status"):
        if user.subscription_status == "active":
            return "1000/minute"  # Premium: 1000 requests/minute
    return RATE_LIMIT_DEFAULT  # Trial/free: default limit


# Determine storage backend
def _get_storage_uri() -> str:
    """
    Get the storage URI for rate limiting.
    Uses Redis if available, falls back to in-memory.

    WARNING: In-memory storage is NOT suitable for production!
    Configure REDIS_URL for production deployments.
    """
    if REDIS_URL:
        try:
            import redis
            # Test Redis connection
            r = redis.from_url(REDIS_URL, socket_timeout=2, socket_connect_timeout=2)
            r.ping()
            logger.info("Rate limiter using Redis storage")
            return REDIS_URL
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting, using memory: {e}")

    # Fallback to in-memory storage with warning
    if IS_PRODUCTION:
        logger.warning(
            "SECURITY WARNING: Rate limiter falling back to in-memory storage in PRODUCTION! "
            "This is NOT recommended. Rate limits will not be shared across instances "
            "and will be lost on restart. Configure REDIS_URL for production deployments."
        )
    else:
        logger.warning(
            "Rate limiter using in-memory storage. "
            "This is acceptable for development but NOT for production. "
            "Configure REDIS_URL for production deployments."
        )
    return "memory://"


# Initialize the limiter with Redis support
limiter = Limiter(
    key_func=get_user_identifier,
    enabled=RATE_LIMIT_ENABLED,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri=_get_storage_uri(),
    strategy="fixed-window",  # Options: fixed-window, moving-window
)


# Rate limit decorators for different endpoint types
def rate_limit_login():
    """Rate limit for login endpoints - strict to prevent brute force."""
    return limiter.limit(RATE_LIMIT_LOGIN, key_func=get_remote_address)


def rate_limit_register():
    """Rate limit for registration - prevent spam accounts."""
    return limiter.limit(RATE_LIMIT_REGISTER, key_func=get_remote_address)


def rate_limit_ai():
    """Rate limit for AI generation endpoints."""
    return limiter.limit(RATE_LIMIT_AI)


def rate_limit_default():
    """Default rate limit for general endpoints."""
    return limiter.limit(RATE_LIMIT_DEFAULT)


def rate_limit_premium(default: str = "100/minute", premium: str = "1000/minute"):
    """
    Dynamic rate limit based on subscription status.

    Args:
        default: Rate limit for trial/free users
        premium: Rate limit for premium subscribers
    """
    def dynamic_limit(request: Request) -> str:
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "subscription_status"):
            if user.subscription_status == "active":
                return premium
        return default

    return limiter.limit(dynamic_limit)


# Export the exception handler
rate_limit_exceeded_handler = _rate_limit_exceeded_handler
