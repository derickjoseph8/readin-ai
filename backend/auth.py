"""Authentication utilities - JWT tokens and password hashing."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Set

import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS, REDIS_URL
from database import get_db
from models import User, StaffRole

logger = logging.getLogger(__name__)

security = HTTPBearer()

# =============================================================================
# TOKEN BLACKLIST WITH REDIS PERSISTENCE
# =============================================================================
# Redis-backed token blacklist for immediate token invalidation.
# Falls back to in-memory storage if Redis is unavailable.
# Uses token hash as key to avoid storing actual tokens in Redis.

_token_blacklist: Set[str] = set()
_redis_client = None

# Initialize Redis connection for token blacklist
try:
    if REDIS_URL:
        import redis
        _redis_client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
        _redis_client.ping()
        logger.info("Token blacklist using Redis storage")
except Exception as e:
    logger.warning(f"Token blacklist falling back to memory: {e}")
    _redis_client = None

# Redis key prefix and TTL for blacklisted tokens
BLACKLIST_KEY_PREFIX = "readin:token_blacklist:"
BLACKLIST_TTL = 60 * 60 * 24 * 8  # 8 days (longer than token expiry)


def _get_token_hash(token: str) -> str:
    """Generate a hash of the token for storage (don't store actual tokens)."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()[:32]


def add_token_to_blacklist(token: str) -> None:
    """
    Add a token to the blacklist, invalidating it immediately.
    Persists to Redis if available, falls back to in-memory.

    Args:
        token: The JWT token to invalidate
    """
    token_hash = _get_token_hash(token)

    # Try Redis first
    if _redis_client:
        try:
            _redis_client.setex(
                f"{BLACKLIST_KEY_PREFIX}{token_hash}",
                BLACKLIST_TTL,
                "1"
            )
            logger.info("Token added to Redis blacklist")
            return
        except Exception as e:
            logger.warning(f"Failed to add token to Redis blacklist: {e}")

    # Fallback to in-memory
    _token_blacklist.add(token_hash)
    logger.info("Token added to in-memory blacklist")


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token has been blacklisted.
    Checks Redis first, then in-memory fallback.

    Args:
        token: The JWT token to check

    Returns:
        True if the token is blacklisted, False otherwise
    """
    token_hash = _get_token_hash(token)

    # Check Redis first
    if _redis_client:
        try:
            if _redis_client.exists(f"{BLACKLIST_KEY_PREFIX}{token_hash}"):
                return True
        except Exception as e:
            logger.warning(f"Failed to check Redis blacklist: {e}")

    # Check in-memory fallback
    return token_hash in _token_blacklist


def clear_expired_tokens_from_blacklist() -> int:
    """
    Remove expired tokens from the in-memory blacklist to prevent memory growth.
    Redis entries auto-expire via TTL.

    This should be called periodically (e.g., via scheduler).
    Returns the number of tokens removed from in-memory storage.
    """
    global _token_blacklist
    # For Redis, tokens auto-expire via TTL - nothing to do
    # For in-memory, we can't easily check expiry since we store hashes
    # Just clear old entries periodically to prevent unbounded growth
    initial_count = len(_token_blacklist)

    # If we have Redis, we can clear in-memory since Redis is source of truth
    if _redis_client:
        _token_blacklist.clear()
        return initial_count

    # Without Redis, keep in-memory but log a warning if it's growing large
    if initial_count > 10000:
        logger.warning(f"In-memory token blacklist has {initial_count} entries - consider enabling Redis")

    return 0


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Encode to bytes, hash, then decode back to string for storage
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(user_id: int) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "exp": expire
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str, request: Optional[Request] = None, check_blacklist: bool = True) -> Optional[int]:
    """
    Decode a JWT token and return user_id.

    Args:
        token: The JWT token to decode
        request: Optional request object for logging context
        check_blacklist: Whether to check if token is blacklisted (default: True)

    Returns:
        The user_id if token is valid, None otherwise
    """
    # Check if token is blacklisted
    if check_blacklist and is_token_blacklisted(token):
        logger.warning(
            "Token verification failed: token is blacklisted",
            extra={
                "ip": request.client.host if request and request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown") if request else "unknown"
            }
        )
        return None

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            logger.warning(
                "Token verification failed: missing 'sub' claim",
                extra={
                    "ip": request.client.host if request and request.client else "unknown",
                    "user_agent": request.headers.get("user-agent", "unknown") if request else "unknown"
                }
            )
            return None
        return int(user_id)
    except JWTError as e:
        logger.warning(
            f"Token verification failed: {str(e)}",
            extra={
                "ip": request.client.host if request and request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown") if request else "unknown",
                "error_type": type(e).__name__
            }
        )
        return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    user_id = decode_token(token, request)

    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        logger.warning(
            f"Token verification failed: user not found",
            extra={
                "user_id": user_id,
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        raise credentials_exception

    # CRITICAL: Auto-restore super admin status for protected accounts
    # This ensures derick@getreadin.ai and derick@getreadin.us ALWAYS have super admin
    if StaffRole.is_protected_super_admin(user.email):
        if user.staff_role != StaffRole.SUPER_ADMIN or not user.is_staff:
            logger.warning(
                f"Restoring super admin status for protected account: {user.email}"
            )
            user.is_staff = True
            user.staff_role = StaffRole.SUPER_ADMIN
            db.commit()

    return user
