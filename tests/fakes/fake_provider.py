"""
tests/fakes/fake_provider.py — Scriptable provider outcomes
──────────────────────────────────────────────────────────
Lets tests define a sequence of outcomes (success, exceptions)
per provider to verify orchestrator fallback, retry, and
circuit-breaker behavior deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from services.generation.errors import (
    ProviderAuthError,
    ProviderInvalidRequestError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderTransientError,
)


@dataclass
class ProviderScript:
    """Declarative script of outcomes for a single provider."""

    outcomes: list = field(default_factory=list)
    _index: int = field(default=0, init=False, repr=False)

    def add_success(self, latency_ms: int = 100) -> "ProviderScript":
        self.outcomes.append(("ok", latency_ms))
        return self

    def add_error(self, exc: Exception) -> "ProviderScript":
        self.outcomes.append(("error", exc))
        return self

    def add_rate_limit(self, retry_after: float = 1.0) -> "ProviderScript":
        self.outcomes.append(
            ("error", ProviderRateLimitError("rate limited", retry_after=retry_after))
        )
        return self

    def add_auth_failure(self) -> "ProviderScript":
        self.outcomes.append(("error", ProviderAuthError("bad key")))
        return self

    def add_quota_exhausted(self) -> "ProviderScript":
        self.outcomes.append(("error", ProviderQuotaError("no quota")))
        return self

    def add_transient(self, msg: str = "timeout") -> "ProviderScript":
        self.outcomes.append(("error", ProviderTransientError(msg)))
        return self

    def add_invalid_request(self, msg: str = "bad params") -> "ProviderScript":
        self.outcomes.append(("error", ProviderInvalidRequestError(msg)))
        return self

    def next(self):
        if self._index >= len(self.outcomes):
            raise RuntimeError("Script exhausted — add more outcomes")
        outcome = self.outcomes[self._index]
        self._index += 1
        return outcome

    def __len__(self) -> int:
        return len(self.outcomes)

    def __iter__(self):
        return iter(self.outcomes)


class ScriptedProvider:
    """
    Minimal provider-like object driven by a ProviderScript.

    The orchestrator calls `generate()`; this object replays
    the scripted outcome — either returning fake bytes or
    raising the scripted exception.
    """

    def __init__(self, provider_id: str, script: ProviderScript):
        self.provider_id = provider_id
        self.script = script
        self.call_count = 0
        self.latencies: list[float] = []

    def generate(self, prompt: str, w: int, h: int, seed: int, cfg: dict, log_cb):
        self.call_count += 1
        kind, payload = self.script.next()
        if kind == "ok":
            self.latencies.append(payload)
            return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, self.provider_id
        raise payload
