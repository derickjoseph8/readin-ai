"""Rate limiting middleware using SlowAPI."""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from typing import Optional, Callable

from config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_LOGIN,
    RATE_LIMIT_REGISTER,
    RATE_LIMIT_AI,
    RATE_LIMIT_DEFAULT,
)


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


# Initialize the limiter
limiter = Limiter(
    key_func=get_user_identifier,
    enabled=RATE_LIMIT_ENABLED,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri="memory://",  # Use Redis in production: redis://localhost:6379
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
