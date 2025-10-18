"""Tests for circuit breaker."""

import time

from football_rag.core.circuit_breaker import CircuitBreaker, CircuitState


def test_breaker_starts_closed():
    """Test that breaker starts in closed state."""
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow() is True


def test_breaker_opens_after_threshold():
    """Test that breaker opens after failure threshold."""
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

    for _ in range(3):
        breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert breaker.allow() is False


def test_breaker_half_open_after_timeout():
    """Test that breaker enters half-open after recovery timeout."""
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    time.sleep(1.1)
    assert breaker.allow() is True
    assert breaker.state == CircuitState.HALF_OPEN


def test_breaker_closes_on_success():
    """Test that breaker closes on successful call."""
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    time.sleep(1.1)
    breaker.allow()
    breaker.record_success()

    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_breaker_resets_on_success():
    """Test that breaker resets failure count on success."""
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

    breaker.record_failure()
    assert breaker.failure_count == 1

    breaker.record_success()
    assert breaker.failure_count == 0
    assert breaker.state == CircuitState.CLOSED
