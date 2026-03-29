import time
from functools import wraps
from typing import Callable, TypeVar, Any, cast

T = TypeVar("T")


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open and the call is not allowed."""


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: float = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                else:
                    raise CircuitBreakerOpenError()

            try:
                result = func(*args, **kwargs)
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.failures = 0
                return result
            except Exception:
                self.failures += 1
                self.last_failure_time = time.time()
                if self.failures >= self.failure_threshold:
                    self.state = "OPEN"
                raise

        return wrapper


# Example usage:
# kms_circuit_breaker = CircuitBreaker()
#
# @kms_circuit_breaker.call
# def sign_with_kms(transaction):
#     return kms_key_manager.sign_transaction(transaction)
