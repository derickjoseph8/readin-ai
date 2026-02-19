"""
Redis caching service for API responses and data.

Provides:
- API response caching
- Database query caching
- Session caching
- Cache invalidation
"""

import json
import logging
import hashlib
from datetime import timedelta
from typing import Optional, Any, Callable, TypeVar
from functools import wraps

from config import REDIS_URL

logger = logging.getLogger("cache")

T = TypeVar("T")


class CacheService:
    """
    Redis-based caching service.

    Falls back gracefully to no-op if Redis is not configured.
    """

    def __init__(self):
        self.client = None
        self.enabled = False

        if REDIS_URL:
            try:
                import redis
                self.client = redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_timeout=2,
                    socket_connect_timeout=2,
                )
                # Test connection
                self.client.ping()
                self.enabled = True
                logger.info("Redis cache connected")
            except ImportError:
                logger.warning("redis package not installed, caching disabled")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, caching disabled")

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if not self.enabled:
            return None

        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300,  # 5 minutes default
    ) -> bool:
        """Set a value in cache with TTL."""
        if not self.enabled:
            return False

        try:
            self.client.setex(
                key,
                ttl_seconds,
                json.dumps(value, default=str),
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self.enabled:
            return False

        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        if not self.enabled:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0

    def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries for a user."""
        self.delete_pattern(f"user:{user_id}:*")

    def invalidate_meeting_cache(self, meeting_id: int):
        """Invalidate all cache entries for a meeting."""
        self.delete_pattern(f"meeting:{meeting_id}:*")

    def get_or_set(
        self,
        key: str,
        fetch_func: Callable[[], T],
        ttl_seconds: int = 300,
    ) -> T:
        """
        Get from cache or fetch and cache.

        Args:
            key: Cache key
            fetch_func: Function to fetch data if not in cache
            ttl_seconds: Cache TTL

        Returns:
            Cached or freshly fetched data
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        value = fetch_func()
        self.set(key, value, ttl_seconds)
        return value

    def cache_stats(self) -> dict:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False}

        try:
            info = self.client.info()
            return {
                "enabled": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0"),
                "total_keys": self.client.dbsize(),
                "hit_rate": info.get("keyspace_hits", 0) / max(
                    info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1
                ),
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}


# Global cache instance
cache = CacheService()


# =============================================================================
# CACHING DECORATORS
# =============================================================================

def cached(
    key_prefix: str,
    ttl_seconds: int = 300,
    key_builder: Optional[Callable] = None,
):
    """
    Decorator to cache function results.

    Usage:
        @cached("user_meetings", ttl_seconds=600)
        def get_user_meetings(user_id: int):
            ...

        @cached("search", key_builder=lambda q, **kw: f"search:{q}")
        def search(query: str, filters: dict):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key: prefix:arg_hash
                arg_str = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
                arg_hash = hashlib.md5(arg_str.encode(), usedforsecurity=False).hexdigest()[:16]
                cache_key = f"{key_prefix}:{arg_hash}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result

        return wrapper
    return decorator


def cached_user(ttl_seconds: int = 300):
    """
    Decorator for caching user-specific data.

    Expects user_id as first argument or in kwargs.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get user_id from args or kwargs
            user_id = kwargs.get("user_id") or (args[0] if args else None)
            if not user_id:
                return func(*args, **kwargs)

            # Build cache key
            func_name = func.__name__
            arg_str = json.dumps(kwargs, sort_keys=True, default=str)
            arg_hash = hashlib.md5(arg_str.encode(), usedforsecurity=False).hexdigest()[:8]
            cache_key = f"user:{user_id}:{func_name}:{arg_hash}"

            # Try cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result

        return wrapper
    return decorator


def invalidate_on_change(patterns: list):
    """
    Decorator to invalidate cache patterns after function execution.

    Usage:
        @invalidate_on_change(["user:{user_id}:*", "meeting:{meeting_id}:*"])
        def update_meeting(user_id: int, meeting_id: int, data: dict):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Invalidate cache patterns
            for pattern in patterns:
                # Replace placeholders with actual values from kwargs
                actual_pattern = pattern
                for key, value in kwargs.items():
                    actual_pattern = actual_pattern.replace(f"{{{key}}}", str(value))
                cache.delete_pattern(actual_pattern)

            return result

        return wrapper
    return decorator


# =============================================================================
# CACHE KEYS
# =============================================================================

class CacheKeys:
    """Standard cache key patterns."""

    @staticmethod
    def user_profile(user_id: int) -> str:
        return f"user:{user_id}:profile"

    @staticmethod
    def user_meetings(user_id: int, page: int = 1) -> str:
        return f"user:{user_id}:meetings:page:{page}"

    @staticmethod
    def meeting_detail(meeting_id: int) -> str:
        return f"meeting:{meeting_id}:detail"

    @staticmethod
    def meeting_summary(meeting_id: int) -> str:
        return f"meeting:{meeting_id}:summary"

    @staticmethod
    def user_analytics(user_id: int, period: str) -> str:
        return f"user:{user_id}:analytics:{period}"

    @staticmethod
    def search_results(query_hash: str) -> str:
        return f"search:{query_hash}"

    @staticmethod
    def health_check() -> str:
        return "system:health"


# =============================================================================
# CACHE TTL CONSTANTS
# =============================================================================

class CacheTTL:
    """Standard TTL values in seconds."""

    VERY_SHORT = 30       # 30 seconds
    SHORT = 60            # 1 minute
    MEDIUM = 300          # 5 minutes
    LONG = 900            # 15 minutes
    VERY_LONG = 3600      # 1 hour
    DAY = 86400           # 24 hours

    # Specific use cases
    PROFILE = MEDIUM
    MEETINGS_LIST = SHORT
    MEETING_DETAIL = MEDIUM
    ANALYTICS = LONG
    SEARCH = SHORT
    HEALTH = VERY_SHORT
    SESSION = DAY         # 24 hours for sessions


# =============================================================================
# SESSION CACHING
# =============================================================================

class SessionCache:
    """
    Redis-based session caching for improved performance.

    Caches user session data to reduce database lookups.
    """

    def __init__(self):
        self.cache = cache
        self.prefix = "session:"

    def _key(self, session_id: str) -> str:
        return f"{self.prefix}{session_id}"

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get cached session data."""
        return self.cache.get(self._key(session_id))

    def set_session(
        self,
        session_id: str,
        data: dict,
        ttl_seconds: int = CacheTTL.SESSION,
    ) -> bool:
        """Cache session data."""
        return self.cache.set(self._key(session_id), data, ttl_seconds)

    def delete_session(self, session_id: str) -> bool:
        """Delete cached session."""
        return self.cache.delete(self._key(session_id))

    def refresh_session(self, session_id: str, ttl_seconds: int = CacheTTL.SESSION) -> bool:
        """Refresh session TTL."""
        if not self.cache.enabled:
            return False

        try:
            self.cache.client.expire(self._key(session_id), ttl_seconds)
            return True
        except Exception:
            return False

    def invalidate_user_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user."""
        return self.cache.delete_pattern(f"{self.prefix}*:user:{user_id}")


# Global session cache instance
session_cache = SessionCache()


# =============================================================================
# API RESPONSE CACHING DECORATOR
# =============================================================================

def cache_response(
    key_prefix: str,
    ttl_seconds: int = CacheTTL.MEDIUM,
    include_user: bool = True,
):
    """
    FastAPI dependency for caching API responses.

    Usage:
        @router.get("/data")
        async def get_data(
            cached = Depends(cache_response("my_data", ttl_seconds=300)),
            db: Session = Depends(get_db),
        ):
            if cached:
                return cached
            # ... fetch data
            # cache.set(key, data, ttl_seconds)
            return data
    """
    async def dependency(request):
        if not cache.enabled:
            return None

        # Build cache key
        user_id = ""
        if include_user:
            user = getattr(request.state, "user", None)
            if user:
                user_id = f":user:{user.id}"

        query_hash = hashlib.md5(str(request.query_params).encode(), usedforsecurity=False).hexdigest()[:8]
        cache_key = f"api:{key_prefix}{user_id}:{query_hash}"

        return cache.get(cache_key)

    return dependency
