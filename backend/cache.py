"""
Redis caching layer for ReadIn AI.

Provides caching for frequently accessed data:
- User session data
- Profession list
- Subscription status
"""

import json
import hashlib
from typing import Any, Optional, Callable, TypeVar
from functools import wraps
from datetime import timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from config import REDIS_URL, IS_PRODUCTION

T = TypeVar('T')


class CacheManager:
    """
    Redis-based cache manager with fallback to in-memory cache.
    """

    # Default TTLs (in seconds)
    TTL_SHORT = 60 * 5         # 5 minutes - session data
    TTL_MEDIUM = 60 * 15       # 15 minutes - user profiles
    TTL_LONG = 60 * 60         # 1 hour - profession list
    TTL_VERY_LONG = 60 * 60 * 4  # 4 hours - static data

    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._memory_cache: dict = {}
        self._connected = False
        self._initialize()

    def _initialize(self):
        """Initialize Redis connection."""
        if not REDIS_AVAILABLE:
            print("  [WARN] Redis library not installed, using memory cache")
            return

        if not REDIS_URL:
            if IS_PRODUCTION:
                print("  [WARN] REDIS_URL not configured, using memory cache")
            return

        try:
            self._redis_client = redis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            # Test connection
            self._redis_client.ping()
            self._connected = True
            print("  [OK] Redis cache connected")
        except Exception as e:
            print(f"  [WARN] Redis connection failed: {e}, using memory cache")
            self._redis_client = None

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self._redis_client is not None

    def _make_key(self, prefix: str, *args) -> str:
        """Generate a cache key."""
        key_parts = [str(arg) for arg in args]
        key_data = ":".join(key_parts)
        return f"readin:{prefix}:{key_data}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self.is_connected:
            try:
                value = self._redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception:
                pass

        # Fallback to memory cache
        cached = self._memory_cache.get(key)
        if cached:
            value, expiry = cached
            import time
            if expiry > time.time():
                return value
            else:
                del self._memory_cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = TTL_MEDIUM) -> bool:
        """Set value in cache."""
        if self.is_connected:
            try:
                self._redis_client.setex(key, ttl, json.dumps(value))
                return True
            except Exception:
                pass

        # Fallback to memory cache
        import time
        self._memory_cache[key] = (value, time.time() + ttl)

        # Limit memory cache size
        if len(self._memory_cache) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k][1]
            )
            for k in sorted_keys[:100]:
                del self._memory_cache[k]

        return True

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if self.is_connected:
            try:
                self._redis_client.delete(key)
            except Exception:
                pass

        if key in self._memory_cache:
            del self._memory_cache[key]

        return True

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        deleted = 0

        if self.is_connected:
            try:
                keys = self._redis_client.keys(pattern)
                if keys:
                    deleted = self._redis_client.delete(*keys)
            except Exception:
                pass

        # Also clear from memory cache
        pattern_prefix = pattern.replace("*", "")
        keys_to_delete = [
            k for k in self._memory_cache.keys()
            if k.startswith(pattern_prefix)
        ]
        for k in keys_to_delete:
            del self._memory_cache[k]
            deleted += 1

        return deleted

    def clear_user_cache(self, user_id: int):
        """Clear all cache entries for a user."""
        self.delete_pattern(f"readin:user:{user_id}:*")
        self.delete(self._make_key("subscription", user_id))
        self.delete(self._make_key("profile", user_id))

    def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = {
            "type": "redis" if self.is_connected else "memory",
            "connected": self.is_connected,
            "memory_cache_size": len(self._memory_cache),
        }

        if self.is_connected:
            try:
                info = self._redis_client.info("memory")
                stats["redis_memory_used"] = info.get("used_memory_human", "unknown")
                stats["redis_keys"] = self._redis_client.dbsize()
            except Exception:
                pass

        return stats


# Global cache instance
cache = CacheManager()


def cached(prefix: str, ttl: int = CacheManager.TTL_MEDIUM, key_args: tuple = None):
    """
    Decorator for caching function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_args: Tuple of argument indices to include in cache key

    Example:
        @cached("user_profile", ttl=300, key_args=(0,))
        def get_user_profile(user_id: int):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Build cache key
            if key_args:
                key_parts = [args[i] for i in key_args if i < len(args)]
            else:
                key_parts = list(args)

            cache_key = cache._make_key(prefix, *key_parts)

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# Cache key generators for common use cases
def user_profile_key(user_id: int) -> str:
    """Generate cache key for user profile."""
    return cache._make_key("profile", user_id)


def subscription_key(user_id: int) -> str:
    """Generate cache key for subscription status."""
    return cache._make_key("subscription", user_id)


def professions_key() -> str:
    """Generate cache key for profession list."""
    return cache._make_key("professions", "all")


def user_meetings_key(user_id: int, page: int = 0) -> str:
    """Generate cache key for user meetings list."""
    return cache._make_key("meetings", user_id, page)
