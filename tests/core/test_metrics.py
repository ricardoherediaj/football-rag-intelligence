"""Tests for metrics collector."""

from football_rag.core.metrics import _Metrics, _percentile


def test_percentile_empty_list():
    """Test percentile with empty list."""
    assert _percentile([], 0.5) == 0


def test_percentile_single_value():
    """Test percentile with single value."""
    assert _percentile([100], 0.5) == 100


def test_percentile_multiple_values():
    """Test percentile calculation."""
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    p50 = _percentile(values, 0.50)
    p95 = _percentile(values, 0.95)
    assert p50 in [50, 60]  # Rough p50 calculation acceptable
    assert p95 in [90, 100]  # Rough p95 calculation acceptable


def test_metrics_increment_requests():
    """Test request counter increment."""
    m = _Metrics()
    assert m.total_requests == 0
    m.increment_requests()
    assert m.total_requests == 1


def test_metrics_increment_errors():
    """Test error counter increment."""
    m = _Metrics()
    assert m.total_errors == 0
    m.increment_errors()
    assert m.total_errors == 1


def test_metrics_record_latency():
    """Test latency recording."""
    m = _Metrics()
    m.record_latency(100)
    m.record_latency(200)
    assert len(m._latencies) == 2


def test_metrics_snapshot():
    """Test metrics snapshot format."""
    m = _Metrics()
    m.increment_requests()
    m.increment_errors()
    m.record_latency(100)
    m.record_latency(200)

    snapshot = m.snapshot()
    assert "total_requests" in snapshot
    assert "total_errors" in snapshot
    assert "p50_ms" in snapshot
    assert "p95_ms" in snapshot
    assert snapshot["total_requests"] == 1
    assert snapshot["total_errors"] == 1
