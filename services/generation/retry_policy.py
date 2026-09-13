"""
services/generation/retry_policy.py — Unified retry/backoff
───────────────────────────────────────────────────────────
Single place that decides *how long* to wait between attempts.
Replaces scattered ``sleep(2)``, ``sleep(3)``, ``sleep(10*attempt)``
previously duplicated across every provider file.
"""
from __future__ import annotations

import random
import time

from services.generation.cancellation import CancellationToken


class RetryPolicy:
    """Exponential backoff with jitter and optional Retry-After support."""

    __slots__ = ("max_attempts", "base_delay", "max_delay", "jitter")

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.5,
        max_delay: float = 20.0,
        jitter: float = 0.25,
    ) -> None:
        self.max_attempts = max(1, max_attempts)
        self.base_delay = max(0.1, base_delay)
        self.max_delay = max(self.base_delay, max_delay)
        self.jitter = max(0.0, min(jitter, 0.9))

    def delay(self, attempt: int, retry_after: float | None = None) -> float:
        """Return seconds to wait before the *next* attempt."""
        if retry_after is not None:
            return min(max(retry_after, 0.0), self.max_delay)
        raw = min(
            self.base_delay * (2 ** max(0, attempt - 1)),
            self.max_delay,
        )
        if self.jitter:
            raw *= 1 + random.uniform(-self.jitter, self.jitter)
        return max(0.01, raw)

    def sleep(self, attempt: int, retry_after: float | None = None) -> None:
        """Convenience: sleep inline (for non-UI-blocking workers)."""
        time.sleep(self.delay(attempt, retry_after))

    def interruptible_sleep(
        self, attempt: int, token: CancellationToken | None = None, retry_after: float | None = None
    ) -> bool:
        """
        Sleep that can be interrupted by cancellation.
        Returns True if interrupted.
        """
        seconds = self.delay(attempt, retry_after)
        if token is None:
            time.sleep(seconds)
            return False
        return token.wait(seconds)


RETRY_POLICIES: dict[str, RetryPolicy] = {
    "default": RetryPolicy(max_attempts=3, base_delay=1.5),
    "aggressive": RetryPolicy(max_attempts=5, base_delay=1.0),
    "conservative": RetryPolicy(max_attempts=2, base_delay=3.0),
}


def get_retry_policy(name: str = "default") -> RetryPolicy:
    return RETRY_POLICIES.get(name, RETRY_POLICIES["default"])
