"""Request context middleware for request ID tracking and logging."""

import time
import uuid
from contextvars import ContextVar
from typing import Optional, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config import IS_PRODUCTION, LOG_LEVEL


# Context variable to store request ID across async boundaries
_request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return _request_id_ctx.get()


def set_request_id(request_id: str) -> None:
    """Set the current request ID in context."""
    _request_id_ctx.set(request_id)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to:
    1. Generate and track unique request IDs
    2. Log request/response timing
    3. Add request metadata to response headers
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # Store in request state for access in routes
        request.state.request_id = request_id

        # Track timing
        start_time = time.perf_counter()

        # Log incoming request
        self._log_request(request, request_id)

        try:
            response = await call_next(request)
        except Exception as e:
            # Log error with request ID
            self._log_error(request, request_id, e, time.perf_counter() - start_time)
            raise

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add tracking headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        # Log response
        self._log_response(request, response, request_id, duration_ms)

        return response

    def _log_request(self, request: Request, request_id: str) -> None:
        """Log incoming request details."""
        # Get client IP
        client_ip = self._get_client_ip(request)

        # Get user agent
        user_agent = request.headers.get("User-Agent", "Unknown")[:100]

        # Format log message
        log_data = {
            "event": "request_started",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params) if request.query_params else None,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }

        if LOG_LEVEL == "DEBUG":
            print(f"[REQUEST] {request.method} {request.url.path} | ID: {request_id[:8]} | IP: {client_ip}")

    def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        duration_ms: float,
    ) -> None:
        """Log response details."""
        status_code = response.status_code
        status_emoji = "OK" if status_code < 400 else "ERR"

        log_data = {
            "event": "request_completed",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }

        if LOG_LEVEL == "DEBUG":
            print(
                f"[RESPONSE] {request.method} {request.url.path} | "
                f"{status_code} {status_emoji} | {duration_ms:.0f}ms | ID: {request_id[:8]}"
            )

    def _log_error(
        self,
        request: Request,
        request_id: str,
        error: Exception,
        duration: float,
    ) -> None:
        """Log error details."""
        duration_ms = duration * 1000

        log_data = {
            "event": "request_error",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],
            "duration_ms": round(duration_ms, 2),
        }

        print(
            f"[ERROR] {request.method} {request.url.path} | "
            f"{type(error).__name__}: {str(error)[:100]} | ID: {request_id[:8]}"
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, considering proxy headers."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP (client IP)
            return forwarded.split(",")[0].strip()

        # Check for real IP header (nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"
