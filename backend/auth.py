"""Authentication utilities - JWT tokens and password hashing."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Set

import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS
from database import get_db
from models import User

logger = logging.getLogger(__name__)

security = HTTPBearer()

# =============================================================================
# TOKEN BLACKLIST
# =============================================================================
# In-memory token blacklist for immediate token invalidation.
# Note: In production with multiple instances, use Redis for shared state.
# Tokens are stored as a set for O(1) lookup.
_token_blacklist: Set[str] = set()


def add_token_to_blacklist(token: str) -> None:
    """
    Add a token to the blacklist, invalidating it immediately.

    Args:
        token: The JWT token to invalidate
    """
    _token_blacklist.add(token)
    logger.info("Token added to blacklist")


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token has been blacklisted.

    Args:
        token: The JWT token to check

    Returns:
        True if the token is blacklisted, False otherwise
    """
    return token in _token_blacklist


def clear_expired_tokens_from_blacklist() -> int:
    """
    Remove expired tokens from the blacklist to prevent memory growth.

    This should be called periodically (e.g., via scheduler).
    Returns the number of tokens removed.
    """
    global _token_blacklist
    initial_count = len(_token_blacklist)
    valid_tokens = set()

    for token in _token_blacklist:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            # Token is still valid (not expired), keep it in blacklist
            valid_tokens.add(token)
        except JWTError:
            # Token is expired or invalid, don't keep it
            pass

    _token_blacklist = valid_tokens
    removed_count = initial_count - len(_token_blacklist)
    if removed_count > 0:
        logger.info(f"Cleared {removed_count} expired tokens from blacklist")
    return removed_count


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

    return user
