"""CSRF Protection Middleware for ReadIn AI."""

import secrets
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from config import JWT_SECRET, IS_PRODUCTION


# CSRF token settings
CSRF_TOKEN_LENGTH = 32
CSRF_TOKEN_HEADER = "X-CSRF-Token"
CSRF_TOKEN_COOKIE = "csrf_token"
CSRF_TOKEN_MAX_AGE = 3600 * 24  # 24 hours


def generate_csrf_token() -> str:
    """Generate a secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def sign_csrf_token(token: str) -> str:
    """Sign a CSRF token with HMAC for integrity verification."""
    signature = hmac.new(
        JWT_SECRET.encode(),
        token.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{token}.{signature}"


def verify_csrf_token(signed_token: str) -> bool:
    """Verify a signed CSRF token."""
    try:
        parts = signed_token.rsplit(".", 1)
        if len(parts) != 2:
            return False

        token, signature = parts
        expected_signature = hmac.new(
            JWT_SECRET.encode(),
            token.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware.

    Protects state-changing requests (POST, PUT, DELETE, PATCH) from
    Cross-Site Request Forgery attacks.

    Implementation:
    - Sets a signed CSRF token in a cookie
    - Requires the token in the X-CSRF-Token header for state-changing requests
    - API endpoints (with Authorization header) are exempt (using JWT instead)
    - GET, HEAD, OPTIONS requests are always allowed
    """

    # Methods that don't require CSRF protection
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    # Paths exempt from CSRF (API endpoints use JWT auth)
    EXEMPT_PATHS = {
        "/api/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/webhooks/",
        "/.well-known/",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if request is exempt
        if self._is_exempt(request):
            return await call_next(request)

        # Safe methods don't need CSRF validation
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            # Set CSRF cookie if not present
            if CSRF_TOKEN_COOKIE not in request.cookies:
                self._set_csrf_cookie(response)
            return response

        # Validate CSRF token for state-changing methods
        if not self._validate_csrf(request):
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing or invalid"
            )

        response = await call_next(request)
        return response

    def _is_exempt(self, request: Request) -> bool:
        """Check if request is exempt from CSRF protection."""
        path = request.url.path

        # API endpoints with Authorization header use JWT
        if "authorization" in request.headers:
            return True

        # Check exempt paths
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return True

        return False

    def _validate_csrf(self, request: Request) -> bool:
        """Validate CSRF token from cookie and header."""
        # Get token from cookie
        cookie_token = request.cookies.get(CSRF_TOKEN_COOKIE)
        if not cookie_token:
            return False

        # Verify cookie token signature
        if not verify_csrf_token(cookie_token):
            return False

        # Get token from header
        header_token = request.headers.get(CSRF_TOKEN_HEADER)
        if not header_token:
            return False

        # Compare tokens (the raw token part, not the signature)
        cookie_raw = cookie_token.rsplit(".", 1)[0]
        header_raw = header_token.rsplit(".", 1)[0] if "." in header_token else header_token

        return hmac.compare_digest(cookie_raw, header_raw)

    def _set_csrf_cookie(self, response: Response) -> None:
        """Set CSRF token cookie."""
        token = generate_csrf_token()
        signed_token = sign_csrf_token(token)

        response.set_cookie(
            key=CSRF_TOKEN_COOKIE,
            value=signed_token,
            max_age=CSRF_TOKEN_MAX_AGE,
            httponly=False,  # JavaScript needs to read this
            samesite="strict" if IS_PRODUCTION else "lax",
            secure=IS_PRODUCTION,
            path="/",
        )


def get_csrf_token(request: Request) -> str:
    """
    Get or generate CSRF token for the current request.

    Use this in form templates to include the token.
    """
    cookie_token = request.cookies.get(CSRF_TOKEN_COOKIE)

    if cookie_token and verify_csrf_token(cookie_token):
        return cookie_token

    # Generate new token
    token = generate_csrf_token()
    return sign_csrf_token(token)
