"""
services/generation/metrics.py — Provider request metrics
──────────────────────────────────────────────────────────
Tracks per-provider request statistics: success rate, latency
percentiles, error counts.  All local, no external reporting.
"""
from __future__ import annotations

import statistics
import threading
import time
from collections import deque


class ProviderMetrics:
    """Tracks request metrics for a single provider."""

    def __init__(self, provider_id: str, window_size: int = 100) -> None:
        self.provider_id = provider_id
        self._window_size = window_size
        self._latencies: deque[float] = deque(maxlen=window_size)
        self._successes = 0
        self._failures = 0
        self._rate_limits = 0
        self._server_errors = 0
        self._timeouts = 0
        self._last_error: str | None = None
        self._last_error_at: float | None = None
        self._lock = threading.RLock()  # Reentrant for nested property access

    def record(self, success: bool, latency_ms: float = 0.0, error_code: str | None = None) -> None:
        with self._lock:
            if success:
                self._successes += 1
                if latency_ms > 0:
                    self._latencies.append(latency_ms)
            else:
                self._failures += 1
                self._last_error = error_code
                self._last_error_at = time.time()
                if error_code == "rate_limited":
                    self._rate_limits += 1
                elif error_code == "transient":
                    self._server_errors += 1
                elif error_code == "timeout":
                    self._timeouts += 1

    @property
    def total_requests(self) -> int:
        with self._lock:
            return self._successes + self._failures

    @property
    def success_rate(self) -> float:
        with self._lock:
            total = self._successes + self._failures
            if total == 0:
                return 1.0
            return self._successes / total

    @property
    def p50_latency(self) -> float:
        with self._lock:
            if not self._latencies:
                return 0.0
            return statistics.median(self._latencies)

    @property
    def p95_latency(self) -> float:
        with self._lock:
            if not self._latencies:
                return 0.0
            sorted_lat = sorted(self._latencies)
            idx = int(len(sorted_lat) * 0.95)
            return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def to_dict(self) -> dict:
        with self._lock:
            latencies_sorted = sorted(self._latencies)
            total = self._successes + self._failures
            return {
                "provider_id": self.provider_id,
                "total": total,
                "successes": self._successes,
                "failures": self._failures,
                "success_rate": self._successes / total if total > 0 else 1.0,
                "p50_latency_ms": statistics.median(latencies_sorted) if latencies_sorted else 0.0,
                "p95_latency_ms": latencies_sorted[int(len(latencies_sorted) * 0.95)] if latencies_sorted else 0.0,
                "rate_limits": self._rate_limits,
                "server_errors": self._server_errors,
                "timeouts": self._timeouts,
                "last_error": self._last_error,
            }


class MetricsCollector:
    """Central collector for all provider metrics."""

    def __init__(self) -> None:
        self._metrics: dict[str, ProviderMetrics] = {}
        self._lock = threading.Lock()

    def get(self, provider_id: str) -> ProviderMetrics:
        with self._lock:
            if provider_id not in self._metrics:
                self._metrics[provider_id] = ProviderMetrics(provider_id)
            return self._metrics[provider_id]

    def record(self, provider_id: str, success: bool, latency_ms: float = 0.0, error_code: str | None = None) -> None:
        self.get(provider_id).record(success, latency_ms, error_code)

    def all(self) -> dict[str, dict]:
        with self._lock:
            return {pid: m.to_dict() for pid, m in self._metrics.items()}

    def summary(self) -> dict:
        all_metrics = self.all()
        total_requests = sum(m["total"] for m in all_metrics.values())
        return {
            "providers": len(all_metrics),
            "total_requests": total_requests,
            "overall_success_rate": (
                sum(m["successes"] for m in all_metrics.values())
                / max(1, total_requests)
            ),
        }


# Global singleton
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    return _metrics_collector
