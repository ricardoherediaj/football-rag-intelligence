"""
Tiny circuit breaker for flaky external calls (e.g., LLM).
Why: fail fast under repeated errors; recover after cooldown.
"""

import time
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._opened_at: float = 0.0

    def allow(self) -> bool:
        if self.state is CircuitState.CLOSED:
            return True
        if (
            self.state is CircuitState.OPEN
            and (time.time() - self._opened_at) >= self.recovery_timeout
        ):
            self.state = CircuitState.HALF_OPEN
            return True
        return self.state is CircuitState.HALF_OPEN

    def record_success(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self._opened_at = time.time()


breaker = CircuitBreaker()
