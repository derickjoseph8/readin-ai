"""
Structured logging middleware for observability.

Provides:
- JSON formatted logs for production
- Request/response logging
- Performance metrics (in-memory and Prometheus)
- Error tracking
- Log sanitization for sensitive data
"""

import time
import logging
import json
import re
from typing import Callable, Dict, Any
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config import IS_PRODUCTION, LOG_LEVEL, LOG_FORMAT


# =============================================================================
# LOG SANITIZATION
# =============================================================================

# Headers that should have their values redacted
SENSITIVE_HEADERS = ["authorization", "x-api-key", "cookie", "x-auth-token", "x-session-id"]

# Regex patterns for sensitive data in request bodies
SENSITIVE_PATTERNS = [
    # Password fields (various naming conventions)
    (re.compile(r'("(?:password|passwd|pwd|pass|secret|credential)["\s]*:\s*")[^"]*(")', re.IGNORECASE), r'\1[REDACTED]\2'),
    # Credit card numbers (16 digit patterns with optional separators)
    (re.compile(r'\b(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?)\d{4}\b'), r'\g<1>****'),
    # API keys (sk-*, pk-*, rk-*, api-*, key-*)
    (re.compile(r'\b(sk-|pk-|rk-|api-|key-)[a-zA-Z0-9]{8,}'), r'\1********'),
    # Bearer tokens
    (re.compile(r'(Bearer\s+)[a-zA-Z0-9\-_.]+', re.IGNORECASE), r'\1[REDACTED]'),
    # SSN patterns
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), r'***-**-****'),
    # Email in certain contexts (optional, for extra privacy)
    # (re.compile(r'("email"\s*:\s*")[^"]+@[^"]+(")', re.IGNORECASE), r'\1[REDACTED]\2'),
]


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact sensitive header values."""
    sanitized = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    return sanitized


def sanitize_body(body: str) -> str:
    """Redact sensitive patterns from request/response body."""
    if not body:
        return body

    sanitized = body
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def sanitize_log_data(log_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize log data dictionary for sensitive information."""
    sanitized = log_data.copy()

    # Sanitize headers if present
    if "headers" in sanitized and isinstance(sanitized["headers"], dict):
        sanitized["headers"] = sanitize_headers(sanitized["headers"])

    # Sanitize body if present
    if "body" in sanitized and isinstance(sanitized["body"], str):
        sanitized["body"] = sanitize_body(sanitized["body"])

    # Sanitize request_body if present
    if "request_body" in sanitized and isinstance(sanitized["request_body"], str):
        sanitized["request_body"] = sanitize_body(sanitized["request_body"])

    # Sanitize any string values that might contain sensitive data
    for key in ["query_params", "path_params"]:
        if key in sanitized and isinstance(sanitized[key], str):
            sanitized[key] = sanitize_body(sanitized[key])

    return sanitized

# Configure structured logging
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

# Configure Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True

    # Prometheus metrics
    HTTP_REQUESTS_TOTAL = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status_code']
    )

    HTTP_REQUEST_DURATION_SECONDS = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint'],
        buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
    )

    HTTP_REQUESTS_IN_PROGRESS = Gauge(
        'http_requests_in_progress',
        'HTTP requests currently in progress',
        ['method', 'endpoint']
    )

    ACTIVE_USERS = Gauge(
        'active_users_total',
        'Number of active users in the system'
    )

    AI_RESPONSE_LATENCY = Histogram(
        'ai_response_latency_seconds',
        'AI response generation latency in seconds',
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
    )

    DATABASE_QUERY_DURATION = Histogram(
        'database_query_duration_seconds',
        'Database query duration in seconds',
        ['operation'],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
    )

except ImportError:
    PROMETHEUS_AVAILABLE = False
    HTTP_REQUESTS_TOTAL = None
    HTTP_REQUEST_DURATION_SECONDS = None
    HTTP_REQUESTS_IN_PROGRESS = None
    ACTIVE_USERS = None
    AI_RESPONSE_LATENCY = None
    DATABASE_QUERY_DURATION = None


def setup_logging():
    """Configure logging based on environment."""
    if STRUCTLOG_AVAILABLE and LOG_FORMAT == "json":
        # JSON logging for production
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        # Standard logging for development
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL, logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


def get_logger(name: str):
    """Get a logger instance."""
    if STRUCTLOG_AVAILABLE and LOG_FORMAT == "json":
        return structlog.get_logger(name)
    return logging.getLogger(name)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.
    """

    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
        self.logger = get_logger("api")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Extract request info
        request_id = request.headers.get("x-request-id", "-")
        start_time = time.time()

        # Get user info if available
        user_id = None
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log request with sanitized data
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", "-")[:100],
        }

        if user_id:
            log_data["user_id"] = user_id

        # Sanitize log data before logging
        log_data = sanitize_log_data(log_data)

        # Log at appropriate level
        if response.status_code >= 500:
            self.logger.error("Request failed", **log_data)
        elif response.status_code >= 400:
            self.logger.warning("Request error", **log_data)
        elif duration_ms > 1000:
            self.logger.warning("Slow request", **log_data)
        else:
            self.logger.info("Request completed", **log_data)

        return response


# Metrics collection
class MetricsCollector:
    """
    Simple in-memory metrics collector.
    For production, integrate with Prometheus or similar.
    """

    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_duration_ms = 0
        self.endpoint_counts = {}
        self.status_counts = {}
        self.start_time = datetime.utcnow()

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float
    ):
        """Record a request for metrics."""
        self.request_count += 1
        self.total_duration_ms += duration_ms

        if status_code >= 400:
            self.error_count += 1

        # Track by endpoint
        endpoint = f"{method} {path}"
        self.endpoint_counts[endpoint] = self.endpoint_counts.get(endpoint, 0) + 1

        # Track by status
        status_group = f"{status_code // 100}xx"
        self.status_counts[status_group] = self.status_counts.get(status_group, 0) + 1

    def get_metrics(self) -> dict:
        """Get current metrics."""
        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        avg_duration = (
            self.total_duration_ms / self.request_count
            if self.request_count > 0 else 0
        )

        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": round(
                self.error_count / self.request_count * 100
                if self.request_count > 0 else 0, 2
            ),
            "avg_response_time_ms": round(avg_duration, 2),
            "requests_per_second": round(
                self.request_count / uptime_seconds
                if uptime_seconds > 0 else 0, 2
            ),
            "status_counts": self.status_counts,
            "top_endpoints": dict(
                sorted(
                    self.endpoint_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            ),
        }

    def reset(self):
        """Reset metrics."""
        self.__init__()


# Global metrics instance
metrics = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting request metrics.
    Records to both in-memory collector and Prometheus.
    """

    def _normalize_path(self, path: str) -> str:
        """Normalize path to prevent high cardinality in metrics."""
        import re
        # Replace UUIDs
        path = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '{id}', path)
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        return path

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        normalized_path = self._normalize_path(request.url.path)

        # Track in-progress requests (Prometheus)
        if PROMETHEUS_AVAILABLE and HTTP_REQUESTS_IN_PROGRESS:
            HTTP_REQUESTS_IN_PROGRESS.labels(
                method=request.method,
                endpoint=normalized_path
            ).inc()

        try:
            response = await call_next(request)
            duration_seconds = time.time() - start_time
            duration_ms = duration_seconds * 1000

            # Record to in-memory collector
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms
            )

            # Record to Prometheus
            if PROMETHEUS_AVAILABLE:
                if HTTP_REQUESTS_TOTAL:
                    HTTP_REQUESTS_TOTAL.labels(
                        method=request.method,
                        endpoint=normalized_path,
                        status_code=str(response.status_code)
                    ).inc()

                if HTTP_REQUEST_DURATION_SECONDS:
                    HTTP_REQUEST_DURATION_SECONDS.labels(
                        method=request.method,
                        endpoint=normalized_path
                    ).observe(duration_seconds)

            return response

        finally:
            # Decrement in-progress counter
            if PROMETHEUS_AVAILABLE and HTTP_REQUESTS_IN_PROGRESS:
                HTTP_REQUESTS_IN_PROGRESS.labels(
                    method=request.method,
                    endpoint=normalized_path
                ).dec()


def get_prometheus_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    if PROMETHEUS_AVAILABLE:
        return generate_latest()
    return b"# Prometheus client not available\n"


def get_prometheus_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    if PROMETHEUS_AVAILABLE:
        return CONTENT_TYPE_LATEST
    return "text/plain"


def record_ai_latency(duration_seconds: float):
    """Record AI response latency."""
    if PROMETHEUS_AVAILABLE and AI_RESPONSE_LATENCY:
        AI_RESPONSE_LATENCY.observe(duration_seconds)


def record_db_query(operation: str, duration_seconds: float):
    """Record database query duration."""
    if PROMETHEUS_AVAILABLE and DATABASE_QUERY_DURATION:
        DATABASE_QUERY_DURATION.labels(operation=operation).observe(duration_seconds)


def set_active_users(count: int):
    """Set the current active users count."""
    if PROMETHEUS_AVAILABLE and ACTIVE_USERS:
        ACTIVE_USERS.set(count)


# Initialize logging on import
setup_logging()
