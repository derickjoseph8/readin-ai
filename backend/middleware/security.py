"""Security middleware for HTTP headers and protections."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable

from config import IS_PRODUCTION, APP_URL


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevent MIME-type sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter (legacy browsers)
    - Strict-Transport-Security: Enforce HTTPS (production only)
    - Content-Security-Policy: Control resource loading
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Control browser features
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy - disable dangerous features
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # HSTS - only in production with HTTPS
        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy
        # Note: 'unsafe-inline' removed from script-src for better XSS protection
        # Use nonces or hashes for inline scripts instead
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' https://js.stripe.com",
            "style-src 'self' 'unsafe-inline'",  # unsafe-inline needed for style attribute
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' https://api.stripe.com https://api.anthropic.com",
            "frame-src https://js.stripe.com",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "upgrade-insecure-requests",  # Upgrade HTTP to HTTPS
            "report-uri /api/v1/csp-report",  # CSP violation reporting endpoint
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response


class TrustedHostMiddleware:
    """
    Validate Host header to prevent host header attacks.

    Only allows requests with expected Host header values.
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: list[str] = None,
        enforce: bool = True,
    ):
        self.app = app
        self.allowed_hosts = allowed_hosts or []
        self.enforce = enforce and IS_PRODUCTION

        # Always allow localhost in development
        if not IS_PRODUCTION:
            self.allowed_hosts.extend([
                "localhost",
                "127.0.0.1",
                "0.0.0.0",
            ])

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        host = headers.get(b"host", b"").decode("latin-1").split(":")[0]

        if self.enforce and host not in self.allowed_hosts:
            # Log suspicious request
            response = Response(
                content='{"detail": "Invalid host header"}',
                status_code=400,
                media_type="application/json",
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
