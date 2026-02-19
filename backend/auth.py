"""Authentication utilities - JWT tokens and password hashing."""

import logging
from datetime import datetime, timedelta
from typing import Optional

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


def decode_token(token: str, request: Optional[Request] = None) -> Optional[int]:
    """Decode a JWT token and return user_id."""
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
