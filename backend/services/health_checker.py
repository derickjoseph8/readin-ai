"""
Enhanced health check service with detailed component status.

Provides comprehensive health monitoring including:
- Database connectivity
- Redis connectivity (if configured)
- External services (Stripe, SendGrid)
- Memory usage
- Application metrics
"""

import time
import psutil
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from sqlalchemy import text
from sqlalchemy.orm import Session

from config import (
    STRIPE_SECRET_KEY, SENDGRID_API_KEY, REDIS_URL,
    APP_NAME, API_VERSION, ENVIRONMENT
)


class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    NOT_CONFIGURED = "not_configured"


class HealthChecker:
    """
    Comprehensive health checking service.

    Checks all system components and returns detailed status.
    """

    def __init__(self, db: Session):
        self.db = db
        self.checks: Dict[str, Dict[str, Any]] = {}
        self.start_time = time.perf_counter()

    def check_all(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        self.checks = {}

        # Run all checks
        self._check_database()
        self._check_redis()
        self._check_stripe()
        self._check_sendgrid()
        self._check_memory()

        # Calculate overall status
        overall_status = self._calculate_overall_status()

        return {
            "status": overall_status,
            "app": APP_NAME,
            "version": API_VERSION,
            "environment": ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": round((time.perf_counter() - self.start_time) * 1000, 2),
            "checks": self.checks,
        }

    def check_basic(self) -> Dict[str, Any]:
        """Run basic health check (fast, for load balancers)."""
        self.checks = {}

        # Only check database
        self._check_database()

        return {
            "status": self.checks.get("database", {}).get("status", HealthStatus.UNHEALTHY),
            "version": API_VERSION,
        }

    def _check_database(self):
        """Check database connectivity."""
        start = time.perf_counter()
        try:
            self.db.execute(text("SELECT 1"))
            self.checks["database"] = {
                "status": HealthStatus.HEALTHY,
                "response_time_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        except Exception as e:
            self.checks["database"] = {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e)[:100],
                "response_time_ms": round((time.perf_counter() - start) * 1000, 2),
            }

    def _check_redis(self):
        """Check Redis connectivity if configured."""
        if not REDIS_URL:
            self.checks["redis"] = {
                "status": HealthStatus.NOT_CONFIGURED,
            }
            return

        start = time.perf_counter()
        try:
            import redis
            client = redis.from_url(REDIS_URL, socket_timeout=2)
            client.ping()
            self.checks["redis"] = {
                "status": HealthStatus.HEALTHY,
                "response_time_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        except ImportError:
            self.checks["redis"] = {
                "status": HealthStatus.NOT_CONFIGURED,
                "error": "redis package not installed",
            }
        except Exception as e:
            self.checks["redis"] = {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e)[:100],
                "response_time_ms": round((time.perf_counter() - start) * 1000, 2),
            }

    def _check_stripe(self):
        """Check Stripe API connectivity."""
        if not STRIPE_SECRET_KEY:
            self.checks["stripe"] = {
                "status": HealthStatus.NOT_CONFIGURED,
            }
            return

        start = time.perf_counter()
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            stripe.Account.retrieve()
            self.checks["stripe"] = {
                "status": HealthStatus.HEALTHY,
                "response_time_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        except Exception as e:
            self.checks["stripe"] = {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e)[:100],
                "response_time_ms": round((time.perf_counter() - start) * 1000, 2),
            }

    def _check_sendgrid(self):
        """Check SendGrid API connectivity."""
        if not SENDGRID_API_KEY:
            self.checks["sendgrid"] = {
                "status": HealthStatus.NOT_CONFIGURED,
            }
            return

        # SendGrid doesn't have a simple ping, so we just verify key format
        if SENDGRID_API_KEY.startswith("SG."):
            self.checks["sendgrid"] = {
                "status": HealthStatus.HEALTHY,
                "note": "API key format valid",
            }
        else:
            self.checks["sendgrid"] = {
                "status": HealthStatus.DEGRADED,
                "warning": "API key format may be invalid",
            }

    def _check_memory(self):
        """Check system memory usage."""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            status = HealthStatus.HEALTHY
            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED

            self.checks["system"] = {
                "status": status,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": memory.percent,
                },
                "cpu_percent": cpu_percent,
            }
        except Exception as e:
            self.checks["system"] = {
                "status": HealthStatus.DEGRADED,
                "error": str(e)[:100],
            }

    def _calculate_overall_status(self) -> str:
        """Calculate overall health status from individual checks."""
        statuses = [check.get("status") for check in self.checks.values()]

        if HealthStatus.UNHEALTHY in statuses:
            # Critical services unhealthy
            if self.checks.get("database", {}).get("status") == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY

        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED

        unhealthy_optional = [
            name for name, check in self.checks.items()
            if check.get("status") == HealthStatus.UNHEALTHY
            and name not in ["database"]  # Non-critical services
        ]

        if unhealthy_optional:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY


def get_health_status(db: Session, detailed: bool = True) -> Dict[str, Any]:
    """
    Get system health status.

    Args:
        db: Database session
        detailed: If True, run all checks; if False, only basic checks

    Returns:
        Health status dictionary
    """
    checker = HealthChecker(db)

    if detailed:
        return checker.check_all()
    else:
        return checker.check_basic()


def is_healthy(db: Session) -> bool:
    """Quick check if system is healthy (for load balancers)."""
    try:
        checker = HealthChecker(db)
        result = checker.check_basic()
        return result.get("status") == HealthStatus.HEALTHY
    except Exception:
        return False
