"""
services/generation/cancellation.py — CancellationToken + Deadline
─────────────────────────────────────────────────────────────────
Thread-safe cancellation and absolute deadline for long-running
generation jobs.  Sleep uses ``Event.wait()`` so cancel()
interrupts immediately instead of blocking for the full delay.
"""
from __future__ import annotations

import threading
import time

from services.generation.errors import DeadlineExceeded, GenerationCancelled


class CancellationToken:
    """Lightweight cooperative cancellation primitive."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def throw_if_cancelled(self) -> None:
        if self._event.is_set():
            raise GenerationCancelled("Job cancelled by user")

    def wait(self, timeout: float) -> bool:
        """
        Wait up to ``timeout`` seconds, returns True if cancelled.
        Unlike ``time.sleep()``, this is immediately interruptible.
        """
        return self._event.wait(timeout)


class Deadline:
    """Absolute deadline shared across all phases of a single job."""

    def __init__(self, seconds: float = 180.0):
        self._deadline = time.monotonic() + max(seconds, 0.1)

    @classmethod
    def from_now(cls, seconds: float = 180.0) -> "Deadline":
        return cls(seconds)

    def remaining(self) -> float:
        return max(0.0, self._deadline - time.monotonic())

    def is_expired(self) -> bool:
        return time.monotonic() >= self._deadline

    def assert_alive(self) -> None:
        if self.is_expired():
            raise DeadlineExceeded(
                f"Deadline exceeded ({self._deadline - time.monotonic():.1f}s ago)"
            )

    def remaining_or_zero(self) -> float:
        return max(0.0, self.remaining())
