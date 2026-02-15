"""Global error handling middleware."""

import traceback
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import IS_PRODUCTION, IS_DEVELOPMENT
from middleware.request_context import get_request_id


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler middleware.

    Catches unhandled exceptions and returns consistent error responses.
    In production, hides internal details. In development, includes stack trace.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            return self._handle_exception(request, exc)

    def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions."""
        request_id = get_request_id()
        error_type = type(exc).__name__

        # Log the full error server-side
        print(f"[UNHANDLED ERROR] {error_type}: {exc}")
        if IS_DEVELOPMENT:
            traceback.print_exc()

        # Build error response
        error_response = {
            "error": True,
            "type": "internal_error",
            "message": self._get_safe_message(exc),
            "request_id": request_id,
        }

        # Include details only in development
        if IS_DEVELOPMENT:
            error_response["detail"] = str(exc)
            error_response["traceback"] = traceback.format_exc()

        return JSONResponse(
            status_code=500,
            content=error_response,
            headers={"X-Request-ID": request_id or "unknown"},
        )

    def _get_safe_message(self, exc: Exception) -> str:
        """Get a safe error message that doesn't leak internal details."""
        # Map known exceptions to user-friendly messages
        exception_messages = {
            "ConnectionError": "Service temporarily unavailable. Please try again.",
            "TimeoutError": "Request timed out. Please try again.",
            "ValueError": "Invalid input provided.",
            "PermissionError": "Access denied.",
            "FileNotFoundError": "Requested resource not found.",
        }

        error_type = type(exc).__name__

        if error_type in exception_messages:
            return exception_messages[error_type]

        # Generic message for production
        if IS_PRODUCTION:
            return "An unexpected error occurred. Please try again later."

        # In development, show the actual error type
        return f"Unhandled {error_type}: {str(exc)[:200]}"


def create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    detail: str = None,
    request_id: str = None,
) -> JSONResponse:
    """
    Create a standardized error response.

    Use this for consistent error formatting across all endpoints.
    """
    response = {
        "error": True,
        "type": error_type,
        "message": message,
    }

    if detail and IS_DEVELOPMENT:
        response["detail"] = detail

    if request_id:
        response["request_id"] = request_id
    else:
        response["request_id"] = get_request_id()

    return JSONResponse(
        status_code=status_code,
        content=response,
    )


# Standard error types
class ErrorTypes:
    """Standard error type constants for consistent error responses."""

    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit_exceeded"
    INTERNAL_ERROR = "internal_error"
    BAD_REQUEST = "bad_request"
    CONFLICT = "conflict"
    SERVICE_UNAVAILABLE = "service_unavailable"
