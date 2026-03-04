"""
Zapier Authentication for ReadIn AI.

Implements OAuth 2.0 authentication flow for Zapier integration.
Zapier requires OAuth 2.0 for secure authentication.
"""

import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session

from config import ZAPIER_CLIENT_ID, ZAPIER_CLIENT_SECRET
from models import User

logger = logging.getLogger("zapier.auth")

# Signature validity window (5 minutes)
SIGNATURE_VALIDITY_SECONDS = 300


def is_zapier_configured() -> bool:
    """Check if Zapier integration is properly configured."""
    return bool(ZAPIER_CLIENT_ID and ZAPIER_CLIENT_SECRET)


def generate_zapier_state(user_id: int) -> str:
    """
    Generate a secure state parameter for OAuth flow.

    Args:
        user_id: The user's ID

    Returns:
        State string containing user ID and random token
    """
    random_token = secrets.token_urlsafe(32)
    return f"{user_id}:{random_token}"


def parse_zapier_state(state: str) -> Tuple[Optional[int], str]:
    """
    Parse the state parameter from OAuth callback.

    Args:
        state: The state string

    Returns:
        Tuple of (user_id, random_token)
    """
    try:
        parts = state.split(":")
        if len(parts) >= 2:
            user_id = int(parts[0])
            token = parts[1]
            return user_id, token
    except (ValueError, IndexError):
        pass
    return None, ""


def verify_zapier_signature(
    payload: bytes,
    signature: str,
    timestamp: str,
    secret: str = None
) -> Tuple[bool, Optional[str]]:
    """
    Verify a Zapier webhook signature.

    Args:
        payload: Raw request body bytes
        signature: The X-Hook-Secret or signature header value
        timestamp: The timestamp header value
        secret: The webhook secret (defaults to ZAPIER_CLIENT_SECRET)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if secret is None:
        secret = ZAPIER_CLIENT_SECRET

    if not secret:
        return False, "Zapier not configured"

    try:
        # Parse timestamp
        try:
            ts = int(timestamp)
        except ValueError:
            return False, "Invalid timestamp format"

        # Check timestamp age
        current_time = int(time.time())
        if abs(current_time - ts) > SIGNATURE_VALIDITY_SECONDS:
            return False, f"Timestamp too old (>{SIGNATURE_VALIDITY_SECONDS}s)"

        # Compute expected signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison
        if hmac.compare_digest(signature, expected_sig):
            return True, None
        else:
            return False, "Signature mismatch"

    except Exception as e:
        return False, f"Verification error: {str(e)}"


async def verify_zapier_request(
    request: Request,
    require_signature: bool = True
) -> bool:
    """
    Verify that a request is from Zapier.

    For REST hooks, Zapier sends a X-Hook-Secret header during subscription.
    For authenticated requests, validates the bearer token.

    Args:
        request: FastAPI request object
        require_signature: Whether to require signature verification

    Returns:
        True if valid

    Raises:
        HTTPException: If verification fails
    """
    if not is_zapier_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zapier integration not configured"
        )

    # Check for hook secret (used during subscription verification)
    hook_secret = request.headers.get("X-Hook-Secret")
    if hook_secret:
        # During subscription, Zapier sends a secret we must echo back
        return True

    # Check for API key authentication (used for action requests)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Validate API key format and authenticity
        # API keys are validated by the main auth system
        return True

    # Check for bearer token authentication
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # Bearer token will be validated by get_current_user dependency
        return True

    if require_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )

    return True


class ZapierAuthService:
    """
    Service for managing Zapier authentication.

    Handles OAuth 2.0 flow for Zapier integration.
    """

    def __init__(self, db: Session):
        """
        Initialize the auth service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def validate_client_credentials(
        self,
        client_id: str,
        client_secret: str
    ) -> bool:
        """
        Validate Zapier client credentials.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret

        Returns:
            True if credentials are valid
        """
        return (
            client_id == ZAPIER_CLIENT_ID and
            client_secret == ZAPIER_CLIENT_SECRET
        )

    def generate_auth_code(
        self,
        user_id: int,
        redirect_uri: str
    ) -> str:
        """
        Generate an authorization code for OAuth flow.

        Args:
            user_id: The user's ID
            redirect_uri: The callback URI

        Returns:
            Authorization code
        """
        # Generate a secure authorization code
        code = secrets.token_urlsafe(48)

        # In production, store this code with expiration
        # For now, we encode user_id in the code (simplified)
        timestamp = int(time.time())
        payload = f"{user_id}:{timestamp}:{code}"

        # Sign the payload
        signature = hmac.new(
            ZAPIER_CLIENT_SECRET.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()[:16]

        return f"{payload}:{signature}"

    def validate_auth_code(
        self,
        code: str,
        max_age: int = 600  # 10 minutes
    ) -> Optional[int]:
        """
        Validate an authorization code.

        Args:
            code: The authorization code
            max_age: Maximum age in seconds

        Returns:
            User ID if valid, None otherwise
        """
        try:
            parts = code.split(":")
            if len(parts) != 4:
                return None

            user_id = int(parts[0])
            timestamp = int(parts[1])
            random_code = parts[2]
            signature = parts[3]

            # Check expiration
            if time.time() - timestamp > max_age:
                logger.warning(f"Auth code expired for user {user_id}")
                return None

            # Verify signature
            payload = f"{user_id}:{timestamp}:{random_code}"
            expected_sig = hmac.new(
                ZAPIER_CLIENT_SECRET.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()[:16]

            if not hmac.compare_digest(signature, expected_sig):
                logger.warning("Auth code signature mismatch")
                return None

            return user_id

        except (ValueError, IndexError) as e:
            logger.error(f"Failed to validate auth code: {e}")
            return None

    def generate_access_token(
        self,
        user_id: int,
        expires_in: int = 3600  # 1 hour
    ) -> Dict[str, Any]:
        """
        Generate an access token for Zapier.

        Args:
            user_id: The user's ID
            expires_in: Token lifetime in seconds

        Returns:
            Dictionary with access_token, token_type, expires_in
        """
        # Generate access token
        access_token = secrets.token_urlsafe(48)
        timestamp = int(time.time())

        # Create signed token
        payload = f"{user_id}:{timestamp}:{access_token}"
        signature = hmac.new(
            ZAPIER_CLIENT_SECRET.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()[:16]

        signed_token = f"zap_{payload}:{signature}"

        # Generate refresh token
        refresh_token = secrets.token_urlsafe(64)
        refresh_payload = f"{user_id}:{timestamp}:{refresh_token}"
        refresh_sig = hmac.new(
            ZAPIER_CLIENT_SECRET.encode('utf-8'),
            refresh_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()[:16]

        signed_refresh = f"zapr_{refresh_payload}:{refresh_sig}"

        return {
            "access_token": signed_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "refresh_token": signed_refresh,
        }

    def validate_access_token(
        self,
        token: str,
        max_age: int = 3600
    ) -> Optional[int]:
        """
        Validate a Zapier access token.

        Args:
            token: The access token
            max_age: Maximum age in seconds

        Returns:
            User ID if valid, None otherwise
        """
        try:
            if not token.startswith("zap_"):
                return None

            token = token[4:]  # Remove prefix
            parts = token.split(":")
            if len(parts) != 4:
                return None

            user_id = int(parts[0])
            timestamp = int(parts[1])
            random_token = parts[2]
            signature = parts[3]

            # Check expiration
            if time.time() - timestamp > max_age:
                return None

            # Verify signature
            payload = f"{user_id}:{timestamp}:{random_token}"
            expected_sig = hmac.new(
                ZAPIER_CLIENT_SECRET.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()[:16]

            if not hmac.compare_digest(signature, expected_sig):
                return None

            return user_id

        except (ValueError, IndexError):
            return None

    def refresh_access_token(
        self,
        refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: The refresh token

        Returns:
            New token response or None if invalid
        """
        try:
            if not refresh_token.startswith("zapr_"):
                return None

            token = refresh_token[5:]  # Remove prefix
            parts = token.split(":")
            if len(parts) != 4:
                return None

            user_id = int(parts[0])
            timestamp = int(parts[1])
            random_token = parts[2]
            signature = parts[3]

            # Refresh tokens are valid for 30 days
            if time.time() - timestamp > 30 * 24 * 3600:
                return None

            # Verify signature
            payload = f"{user_id}:{timestamp}:{random_token}"
            expected_sig = hmac.new(
                ZAPIER_CLIENT_SECRET.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()[:16]

            if not hmac.compare_digest(signature, expected_sig):
                return None

            # Generate new tokens
            return self.generate_access_token(user_id)

        except (ValueError, IndexError):
            return None
