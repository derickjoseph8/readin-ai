"""Slow query logging middleware for database performance monitoring."""

import logging
import time
from typing import Optional
from contextlib import contextmanager
from functools import wraps

from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import LOG_LEVEL, IS_DEVELOPMENT

# Configure logger
logger = logging.getLogger("slow_query")
logger.setLevel(logging.WARNING)

# Default threshold in milliseconds (reduced from 500ms to catch more slow queries)
SLOW_QUERY_THRESHOLD_MS = 100


class SlowQueryLogger:
    """
    Logs slow database queries for performance monitoring.

    Tracks queries that exceed a configurable threshold and logs
    query text, parameters, and execution time.
    """

    def __init__(self, threshold_ms: int = SLOW_QUERY_THRESHOLD_MS):
        self.threshold_ms = threshold_ms
        self._enabled = True

    def enable(self):
        """Enable slow query logging."""
        self._enabled = True

    def disable(self):
        """Disable slow query logging."""
        self._enabled = False

    def set_threshold(self, threshold_ms: int):
        """Set the slow query threshold in milliseconds."""
        self.threshold_ms = threshold_ms

    def log_query(self, query: str, params: dict, duration_ms: float):
        """Log a slow query."""
        if not self._enabled:
            return

        if duration_ms >= self.threshold_ms:
            # Truncate very long queries
            query_display = query[:1000] + "..." if len(query) > 1000 else query

            logger.warning(
                "Slow query detected",
                extra={
                    "query": query_display,
                    "params": str(params)[:500] if params else None,
                    "duration_ms": round(duration_ms, 2),
                    "threshold_ms": self.threshold_ms,
                }
            )

            # In development, also print to console
            if IS_DEVELOPMENT:
                print(f"\n[SLOW QUERY] {duration_ms:.2f}ms (threshold: {self.threshold_ms}ms)")
                print(f"  Query: {query_display[:200]}...")
                print()


# Global slow query logger instance
slow_query_logger = SlowQueryLogger()


def setup_slow_query_logging(engine: Engine, threshold_ms: int = SLOW_QUERY_THRESHOLD_MS):
    """
    Set up slow query logging for a SQLAlchemy engine.

    Args:
        engine: SQLAlchemy engine instance
        threshold_ms: Threshold in milliseconds for slow queries
    """
    slow_query_logger.set_threshold(threshold_ms)

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        conn.info.setdefault("query_start_time", []).append(time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Check query duration and log if slow."""
        start_times = conn.info.get("query_start_time", [])
        if start_times:
            start_time = start_times.pop()
            duration_ms = (time.perf_counter() - start_time) * 1000

            slow_query_logger.log_query(
                query=statement,
                params=parameters,
                duration_ms=duration_ms
            )


@contextmanager
def track_query_time():
    """
    Context manager to track query execution time.

    Usage:
        with track_query_time() as tracker:
            db.query(User).all()
        print(f"Query took {tracker.duration_ms}ms")
    """
    class Tracker:
        def __init__(self):
            self.start_time = time.perf_counter()
            self.duration_ms = 0

        def finish(self):
            self.duration_ms = (time.perf_counter() - self.start_time) * 1000

    tracker = Tracker()
    try:
        yield tracker
    finally:
        tracker.finish()


def log_slow_queries(threshold_ms: int = SLOW_QUERY_THRESHOLD_MS):
    """
    Decorator to log slow database operations.

    Usage:
        @log_slow_queries(threshold_ms=200)
        def get_user_meetings(user_id: int, db: Session):
            return db.query(Meeting).filter(Meeting.user_id == user_id).all()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                if duration_ms >= threshold_ms:
                    logger.warning(
                        f"Slow operation: {func.__name__}",
                        extra={
                            "function": func.__name__,
                            "duration_ms": round(duration_ms, 2),
                            "threshold_ms": threshold_ms,
                        }
                    )
        return wrapper
    return decorator
