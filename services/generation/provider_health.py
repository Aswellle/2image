"""
services/generation/provider_health.py — Health tracking & circuit breaker
────────────────────────────────────────────────────────────────────────
Tracks per-provider success rate, latency, consecutive failures,
and implements a simple circuit breaker (HEALTHY → DEGRADED → OPEN → HALF_OPEN).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field



class HealthState:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ProviderHealth:
    """Mutable health record for a single provider."""

    provider_id: str
    consecutive_failures: int = 0
    successes: int = 0
    failures: int = 0
    avg_latency_ms: float = 0.0
    last_error_code: str | None = None
    last_failure_at: float | None = None
    cooldown_until: float | None = None
    _state: str = HealthState.HEALTHY
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # Thresholds
    DEGRADE_THRESHOLD: int = field(default=3, init=False)
    OPEN_THRESHOLD: int = field(default=5, init=False)
    COOLDOWN_SECONDS: float = field(default=30.0, init=False)
    HALF_OPEN_MAX: int = field(default=1, init=False)

    def record_success(self, latency_ms: float = 0.0) -> None:
        with self._lock:
            self.successes += 1
            self.consecutive_failures = 0
            if latency_ms > 0:
                # Exponential moving average
                if self.avg_latency_ms == 0:
                    self.avg_latency_ms = latency_ms
                else:
                    self.avg_latency_ms = self.avg_latency_ms * 0.7 + latency_ms * 0.3
            if self._state == HealthState.HALF_OPEN:
                self._state = HealthState.HEALTHY
                self.cooldown_until = None

    def record_failure(self, error_code: str | None = None) -> None:
        with self._lock:
            self.failures += 1
            self.consecutive_failures += 1
            self.last_error_code = error_code
            self.last_failure_at = time.monotonic()

            if self.consecutive_failures >= self.OPEN_THRESHOLD:
                self._state = HealthState.OPEN
                self.cooldown_until = time.monotonic() + self.COOLDOWN_SECONDS
            elif self.consecutive_failures >= self.DEGRADE_THRESHOLD:
                self._state = HealthState.DEGRADED

    @property
    def state(self) -> str:
        with self._lock:
            # Check if cooldown expired for OPEN state
            if self._state == HealthState.OPEN and self.cooldown_until:
                if time.monotonic() >= self.cooldown_until:
                    self._state = HealthState.HALF_OPEN
            return self._state

    @property
    def is_available(self) -> bool:
        """Can this provider be tried?"""
        return self.state in (HealthState.HEALTHY, HealthState.DEGRADED, HealthState.HALF_OPEN)

    @property
    def success_rate(self) -> float:
        with self._lock:
            total = self.successes + self.failures
            if total == 0:
                return 1.0  # No data = assume healthy
            return self.successes / total

    def score(self) -> float:
        """
        Routing score: higher = better candidate.
        Used by the health-aware router.
        """
        state = self.state
        if state == HealthState.OPEN:
            return 0.0
        base = 100.0
        if state == HealthState.DEGRADED:
            base -= 40.0
        elif state == HealthState.HALF_OPEN:
            base -= 20.0
        # Penalize high failure rate
        base *= self.success_rate
        # Penalize high latency
        if self.avg_latency_ms > 0:
            latency_penalty = min(30.0, self.avg_latency_ms / 100.0)
            base -= latency_penalty
        return max(0.0, base)


class HealthRegistry:
    """Thread-safe registry of all provider health records."""

    def __init__(self) -> None:
        self._health: dict[str, ProviderHealth] = {}
        self._lock = threading.Lock()

    def get(self, provider_id: str) -> ProviderHealth:
        with self._lock:
            if provider_id not in self._health:
                self._health[provider_id] = ProviderHealth(provider_id)
            return self._health[provider_id]

    def get_or_create(self, provider_id: str) -> ProviderHealth:
        return self.get(provider_id)

    def all(self) -> dict[str, ProviderHealth]:
        with self._lock:
            return dict(self._health)

    def available_ids(self) -> list[str]:
        with self._lock:
            return [pid for pid, h in self._health.items() if h.is_available]

    def reset(self, provider_id: str | None = None) -> None:
        with self._lock:
            if provider_id:
                self._health.pop(provider_id, None)
            else:
                self._health.clear()


# Global singleton
_health_registry = HealthRegistry()


def get_health_registry() -> HealthRegistry:
    """Get the global health registry instance."""
    return _health_registry
