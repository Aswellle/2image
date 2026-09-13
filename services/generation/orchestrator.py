"""
services/generation/orchestrator.py — Task-level generation orchestrator
────────────────────────────────────────────────────────────────────────
Replaces the linear fallback loop in image_service.generate_image()
with a structured orchestrator that:
  - Respects CancellationToken and Deadline
  - Uses RetryPolicy for provider-level retries
  - Tracks ProviderHealth for circuit-breaking
  - Classifies errors via ProviderError taxonomy
  - Only falls back on fallback=True errors
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable

from services.generation.cancellation import CancellationToken, Deadline
from services.generation.errors import (
    GenerationCancelled,
    ProviderError,
    ProviderTransientError,
)
from services.generation.provider_health import get_health_registry
from services.generation.retry_policy import RetryPolicy, get_retry_policy


log = logging.getLogger(__name__)


@dataclass
class OrchestratorResult:
    """Result of an orchestration attempt."""

    image_bytes: bytes | None = None
    provider_id: str | None = None
    attempts: int = 0
    errors: list[str] = None
    duration_ms: float = 0.0
    cancelled: bool = False
    deadline_exceeded: bool = False

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class GenerationOrchestrator:
    """
    Orchestrates image generation across multiple providers.

    Usage::

        orch = GenerationOrchestrator(
            providers={"siliconflow": fn1, "gemini": fn2},
            retry_policy=RetryPolicy(max_attempts=2),
        )
        result = orch.run("a cat", 1024, 1024, 42, cfg, log_cb=print)
    """

    def __init__(
        self,
        providers: dict[str, Callable],
        retry_policy: RetryPolicy | None = None,
        deadline_seconds: float = 180.0,
    ) -> None:
        self.providers = providers
        self.retry_policy = retry_policy or get_retry_policy("default")
        self.deadline_seconds = deadline_seconds

    def run(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int,
        cfg: dict,
        log_cb: Callable[[str], None] | None = None,
        status_cb: Callable[[str], None] | None = None,
        token: CancellationToken | None = None,
        provider_order: list[str] | None = None,
    ) -> OrchestratorResult:
        """
        Try providers in order until success or exhaustion.
        """
        result = OrchestratorResult()
        deadline = Deadline(self.deadline_seconds)
        health_reg = get_health_registry()

        order = provider_order or list(self.providers.keys())
        start_time = time.monotonic()

        for provider_id in order:
            # Check cancellation/deadline before each provider
            if token:
                token.throw_if_cancelled()
            if deadline.is_expired():
                result.deadline_exceeded = True
                break

            # Skip unhealthy providers
            health = health_reg.get(provider_id)
            if not health.is_available:
                msg = f"Skipping {provider_id} (state={health.state})"
                log.debug(msg)
                if log_cb:
                    log_cb(f"⏭ {msg}")
                continue

            fn = self.providers.get(provider_id)
            if fn is None:
                continue

            # Try this provider with retries
            for attempt in range(1, self.retry_policy.max_attempts + 1):
                if token:
                    token.throw_if_cancelled()
                if deadline.is_expired():
                    result.deadline_exceeded = True
                    break

                msg = f"[{provider_id}] attempt {attempt}/{self.retry_policy.max_attempts}"
                if status_cb:
                    status_cb(f"⏳ {provider_id} (尝试 {attempt})…")


                if log_cb:
                    log_cb(f"=== {msg} ===")

                try:
                    ps = time.monotonic()
                    # Support both callables and objects with .generate()
                    if callable(fn):
                        image_bytes, used_provider = fn(
                            prompt, width, height, seed, cfg, log_cb
                        )
                    else:
                        image_bytes, used_provider = fn.generate(
                            prompt, width, height, seed, cfg, log_cb
                        )
                    latency_ms = (time.monotonic() - ps) * 1000



                    health.record_success(latency_ms)
                    result.image_bytes = image_bytes
                    result.provider_id = used_provider
                    result.attempts += 1
                    result.duration_ms = (time.monotonic() - start_time) * 1000

                    if log_cb:
                        log_cb(f"✓ {provider_id} 成功 ({latency_ms:.0f}ms)")
                    return result

                except GenerationCancelled:
                    result.cancelled = True
                    if log_cb:
                        log_cb("✗ 用户取消")


                except ProviderError as exc:
                    result.attempts += 1
                    health.record_failure(exc.code)
                    error_msg = f"[{provider_id}] {exc.code}: {exc}"
                    result.errors.append(error_msg)

                    if log_cb:
                        log_cb(f"✗ {error_msg}")

                    if not exc.retryable:
                        # Don't retry this provider, move to next
                        if status_cb:
                            status_cb(f"⚠ {provider_id}: {exc.code}")
                        break

                    # Retryable: apply backoff then retry
                    if attempt < self.retry_policy.max_attempts:
                        retry_after = getattr(exc, "retry_after", None)
                        interrupted = self.retry_policy.interruptible_sleep(
                            attempt, token, retry_after
                        )
                        if interrupted:
                            result.cancelled = True
                            raise GenerationCancelled("Cancelled during retry wait")

                except Exception as exc:
                    # Unknown error — classify as transient
                    result.attempts += 1
                    mapped = ProviderTransientError(f"{type(exc).__name__}: {exc}")
                    health.record_failure(mapped.code)
                    error_msg = f"[{provider_id}] unexpected: {exc}"
                    result.errors.append(error_msg)

                    if log_cb:
                        log_cb(f"✗ {error_msg}")

                    if attempt < self.retry_policy.max_attempts:
                        interrupted = self.retry_policy.interruptible_sleep(
                            attempt, token
                        )
                        if interrupted:
                            result.cancelled = True
                            raise GenerationCancelled("Cancelled during retry wait")

            if result.deadline_exceeded or result.cancelled:
                break

        # All providers exhausted
        result.duration_ms = (time.monotonic() - start_time) * 1000
        return result
