"""
In-memory metrics for /metrics endpoint (rough p50/p95).
Why: quick visibility for a POC without Prometheus.
"""

from typing import Dict, List


def _percentile(values: List[int], p: float) -> int:
    if not values:
        return 0
    idx = max(0, min(len(values) - 1, int(len(values) * p)))
    return sorted(values)[idx]


class _Metrics:
    def __init__(self) -> None:
        self.total_requests = 0
        self.total_errors = 0
        self._latencies: List[int] = []

    def increment_requests(self) -> None:
        self.total_requests += 1

    def increment_errors(self) -> None:
        self.total_errors += 1

    def record_latency(self, ms: int) -> None:
        self._latencies.append(ms)
        # TODO: cap to last N samples if memory grows

    def snapshot(self) -> Dict[str, int]:
        lat = list(self._latencies)
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "p50_ms": _percentile(lat, 0.50),
            "p95_ms": _percentile(lat, 0.95),
        }


metrics = _Metrics()
