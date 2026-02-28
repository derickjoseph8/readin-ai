"""Response time monitoring middleware for API performance tracking."""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

# In-memory metrics storage (use Redis in production for multi-instance)
_metrics_lock = threading.Lock()
_endpoint_metrics = defaultdict(lambda: {
    "count": 0,
    "total_ms": 0.0,
    "max_ms": 0.0,
    "slow_count": 0
})

# Slow request threshold in milliseconds
SLOW_REQUEST_THRESHOLD_MS = 1000


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track and log API response times.

    Features:
    - Adds X-Response-Time header to all responses
    - Logs slow requests (>1 second)
    - Tracks metrics per endpoint
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add response time header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        # Get endpoint path (normalize to avoid cardinality explosion)
        endpoint = self._normalize_path(request.url.path)

        # Update metrics
        with _metrics_lock:
            metrics = _endpoint_metrics[endpoint]
            metrics["count"] += 1
            metrics["total_ms"] += duration_ms
            metrics["max_ms"] = max(metrics["max_ms"], duration_ms)

            if duration_ms >= SLOW_REQUEST_THRESHOLD_MS:
                metrics["slow_count"] += 1

        # Log slow requests
        if duration_ms >= SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {duration_ms:.2f}ms (threshold: {SLOW_REQUEST_THRESHOLD_MS}ms)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "status_code": response.status_code,
                    "client_ip": request.client.host if request.client else None,
                }
            )

        return response

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to prevent cardinality explosion in metrics.

        Replaces numeric IDs with placeholders:
        /api/v1/meetings/123 -> /api/v1/meetings/{id}
        """
        parts = path.split("/")
        normalized = []
        for part in parts:
            if part.isdigit():
                normalized.append("{id}")
            elif self._looks_like_uuid(part):
                normalized.append("{uuid}")
            else:
                normalized.append(part)
        return "/".join(normalized)

    def _looks_like_uuid(self, s: str) -> bool:
        """Check if string looks like a UUID."""
        if len(s) in (32, 36):
            cleaned = s.replace("-", "")
            return len(cleaned) == 32 and all(c in "0123456789abcdefABCDEF" for c in cleaned)
        return False


def get_response_time_metrics() -> dict:
    """
    Get current response time metrics for all endpoints.

    Returns:
        Dictionary with metrics per endpoint including:
        - count: Total requests
        - avg_ms: Average response time
        - max_ms: Maximum response time
        - slow_count: Number of slow requests
    """
    with _metrics_lock:
        result = {}
        for endpoint, metrics in _endpoint_metrics.items():
            if metrics["count"] > 0:
                result[endpoint] = {
                    "count": metrics["count"],
                    "avg_ms": round(metrics["total_ms"] / metrics["count"], 2),
                    "max_ms": round(metrics["max_ms"], 2),
                    "slow_count": metrics["slow_count"],
                }
        return result


def reset_metrics():
    """Reset all metrics. Useful for testing."""
    global _endpoint_metrics
    with _metrics_lock:
        _endpoint_metrics.clear()
