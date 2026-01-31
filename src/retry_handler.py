"""Retry handler with exponential backoff for network operations."""

import time
import functools
from typing import Callable, Optional, Type, Tuple, Any
import threading


class RetryError(Exception):
    """Exception raised when all retry attempts are exhausted."""

    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


class CircuitBreaker:
    """Circuit breaker pattern for preventing repeated failed calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_requests: int = 1
    ):
        """Initialize the circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_requests: Number of test requests in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests

        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._state = 'closed'  # 'closed', 'open', 'half_open'
        self._half_open_successes = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        """Get the current circuit state."""
        with self._lock:
            self._check_recovery()
            return self._state

    def _check_recovery(self):
        """Check if circuit should move to half-open state."""
        if self._state == 'open' and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = 'half_open'
                self._half_open_successes = 0

    def record_success(self):
        """Record a successful call."""
        with self._lock:
            if self._state == 'half_open':
                self._half_open_successes += 1
                if self._half_open_successes >= self.half_open_requests:
                    self._state = 'closed'
                    self._failures = 0
            elif self._state == 'closed':
                self._failures = 0

    def record_failure(self):
        """Record a failed call."""
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()

            if self._state == 'half_open':
                self._state = 'open'
            elif self._failures >= self.failure_threshold:
                self._state = 'open'

    def is_open(self) -> bool:
        """Check if circuit is open (calls should be blocked)."""
        with self._lock:
            self._check_recovery()
            return self._state == 'open'

    def reset(self):
        """Reset the circuit breaker."""
        with self._lock:
            self._failures = 0
            self._last_failure_time = None
            self._state = 'closed'
            self._half_open_successes = 0


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    circuit_breaker: Optional[CircuitBreaker] = None
):
    """Decorator that adds retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including first try)
        backoff_factor: Multiplier for delay between attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        retry_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called on each retry (exception, attempt_number)
        circuit_breaker: Optional circuit breaker instance

    Example:
        @with_retry(max_attempts=3, backoff_factor=2)
        def api_call():
            response = requests.get(url)
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Check circuit breaker
            if circuit_breaker and circuit_breaker.is_open():
                raise RetryError(
                    "Circuit breaker is open - service unavailable",
                    None
                )

            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    return result

                except retry_exceptions as e:
                    last_exception = e

                    if circuit_breaker:
                        circuit_breaker.record_failure()

                    if attempt < max_attempts:
                        if on_retry:
                            on_retry(e, attempt)

                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        raise RetryError(
                            f"Failed after {max_attempts} attempts: {str(e)}",
                            last_exception
                        )

        return wrapper
    return decorator


async def with_retry_async(
    func: Callable,
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Any:
    """Async version of retry logic.

    Args:
        func: Async function to call
        max_attempts: Maximum number of attempts
        backoff_factor: Multiplier for delay between attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        retry_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called on each retry

    Returns:
        Result of the function call

    Example:
        result = await with_retry_async(
            lambda: fetch_data(),
            max_attempts=3
        )
    """
    import asyncio

    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = await func()
            return result

        except retry_exceptions as e:
            last_exception = e

            if attempt < max_attempts:
                if on_retry:
                    on_retry(e, attempt)

                await asyncio.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)
            else:
                raise RetryError(
                    f"Failed after {max_attempts} attempts: {str(e)}",
                    last_exception
                )


class RetryableRequest:
    """Context manager for retryable operations with state tracking."""

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0
    ):
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay

        self.attempt = 0
        self.delay = initial_delay
        self.last_exception: Optional[Exception] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def should_retry(self, exception: Exception) -> bool:
        """Check if operation should be retried.

        Args:
            exception: The exception that occurred

        Returns:
            True if should retry, False otherwise
        """
        self.attempt += 1
        self.last_exception = exception

        if self.attempt >= self.max_attempts:
            return False

        # Wait before retry
        time.sleep(self.delay)
        self.delay = self.delay * self.backoff_factor

        return True

    def get_status(self) -> dict:
        """Get current retry status."""
        return {
            'attempt': self.attempt,
            'max_attempts': self.max_attempts,
            'next_delay': self.delay,
            'last_exception': str(self.last_exception) if self.last_exception else None
        }
