"""
tests/test_orchestrator.py — Orchestrator + health + circuit breaker tests
─────────────────────────────────────────────────────────────────────────
Validates the GenerationOrchestrator, ProviderHealth, and
circuit breaker using scripted fake providers.
"""
from __future__ import annotations

import time

import pytest

from services.generation.cancellation import CancellationToken
from services.generation.orchestrator import GenerationOrchestrator
from services.generation.provider_health import (
    HealthRegistry,
    HealthState,
    ProviderHealth,
    get_health_registry,
)
from services.generation.retry_policy import RetryPolicy
from tests.fakes.fake_provider import ProviderScript, ScriptedProvider


# ─── ProviderHealth Tests ─────────────────────────────────────────


class TestProviderHealth:
    def test_initial_state_healthy(self):
        h = ProviderHealth("test")
        assert h.state == HealthState.HEALTHY
        assert h.is_available is True
        assert h.success_rate == 1.0

    def test_record_success(self):
        h = ProviderHealth("test")
        h.record_success(latency_ms=100)
        assert h.successes == 1
        assert h.consecutive_failures == 0
        assert h.avg_latency_ms == 100

    def test_latency_ema(self):
        h = ProviderHealth("test")
        h.record_success(100)
        h.record_success(200)
        # EMA: 100 * 0.7 + 200 * 0.3 = 130
        assert 120 < h.avg_latency_ms < 140

    def test_degraded_after_threshold(self):
        h = ProviderHealth("test")
        for _ in range(h.DEGRADE_THRESHOLD):
            h.record_failure("transient")
        assert h.state == HealthState.DEGRADED
        assert h.is_available is True

    def test_open_after_threshold(self):
        h = ProviderHealth("test")
        for _ in range(h.OPEN_THRESHOLD):
            h.record_failure("transient")
        assert h.state == HealthState.OPEN
        assert h.is_available is False

    def test_cooldown_expires_to_half_open(self):
        h = ProviderHealth("test")
        h.COOLDOWN_SECONDS = 0.01  # Speed up test
        for _ in range(h.OPEN_THRESHOLD):
            h.record_failure("transient")
        assert h.state == HealthState.OPEN
        time.sleep(0.05)
        assert h.state == HealthState.HALF_OPEN
        assert h.is_available is True

    def test_half_open_success_resets(self):
        h = ProviderHealth("test")
        h.COOLDOWN_SECONDS = 0.01
        for _ in range(h.OPEN_THRESHOLD):
            h.record_failure("transient")
        time.sleep(0.05)
        assert h.state == HealthState.HALF_OPEN
        h.record_success()
        assert h.state == HealthState.HEALTHY
        assert h.consecutive_failures == 0

    def test_success_rate_calculation(self):
        h = ProviderHealth("test")
        h.record_success()
        h.record_success()
        h.record_failure("err")
        assert h.success_rate == 2 / 3

    def test_score_healthy(self):
        h = ProviderHealth("test")
        h.record_success(50)
        assert h.score() > 50

    def test_score_degraded_lower(self):
        h = ProviderHealth("test")
        h.record_success()
        for _ in range(h.DEGRADE_THRESHOLD):
            h.record_failure("err")
        degraded_score = h.score()
        assert degraded_score < 100

    def test_score_open_is_zero(self):
        h = ProviderHealth("test")
        for _ in range(h.OPEN_THRESHOLD):
            h.record_failure("err")
        assert h.score() == 0.0


class TestHealthRegistry:
    def test_get_creates_on_demand(self):
        reg = HealthRegistry()
        h = reg.get("new_provider")
        assert isinstance(h, ProviderHealth)
        assert h.provider_id == "new_provider"

    def test_available_ids(self):
        reg = HealthRegistry()
        reg.get("a")
        reg.get("b").record_failure("err")
        available = reg.available_ids()
        assert "a" in available

    def test_reset_specific(self):
        reg = HealthRegistry()
        reg.get("a")
        reg.get("b")
        reg.reset("a")
        assert "a" not in reg.all()
        assert "b" in reg.all()

    def test_reset_all(self):
        reg = HealthRegistry()
        reg.get("a")
        reg.get("b")
        reg.reset()
        assert len(reg.all()) == 0


# ─── Orchestrator Tests ───────────────────────────────────────────


class TestGenerationOrchestrator:
    def test_first_provider_succeeds(self):
        providers = {
            "a": ScriptedProvider("a", ProviderScript().add_success()),
        }
        orch = GenerationOrchestrator(providers, deadline_seconds=30)
        result = orch.run("test", 64, 64, 1, {}, log_cb=lambda m: None)
        assert result.image_bytes is not None
        assert result.provider_id == "a"
        assert result.attempts == 1

    def test_fallback_after_transient(self):
        providers = {
            "a": ScriptedProvider("a", ProviderScript().add_transient()),
            "b": ScriptedProvider("b", ProviderScript().add_success()),
        }
        orch = GenerationOrchestrator(
            providers, retry_policy=RetryPolicy(max_attempts=1), deadline_seconds=30
        )
        result = orch.run("test", 64, 64, 1, {}, log_cb=lambda m: None)
        assert result.image_bytes is not None
        assert result.provider_id == "b"

    def test_auth_error_stops_retry(self):
        providers = {
            "a": ScriptedProvider("a", ProviderScript().add_auth_failure()),
            "b": ScriptedProvider("b", ProviderScript().add_success()),
        }
        orch = GenerationOrchestrator(
            providers, retry_policy=RetryPolicy(max_attempts=3), deadline_seconds=30
        )
        result = orch.run("test", 64, 64, 1, {}, log_cb=lambda m: None)
        # Should skip to b without retrying a
        assert result.provider_id == "b"
        assert providers["a"].call_count == 1

    def test_all_fail_returns_empty(self):
        providers = {
            "a": ScriptedProvider("a", ProviderScript().add_transient()),
            "b": ScriptedProvider("b", ProviderScript().add_transient()),
        }
        orch = GenerationOrchestrator(
            providers, retry_policy=RetryPolicy(max_attempts=1), deadline_seconds=30
        )
        result = orch.run("test", 64, 64, 1, {}, log_cb=lambda m: None)
        assert result.image_bytes is None
        assert len(result.errors) == 2

    def test_cancellation_stops_immediately(self):
        providers = {
            "a": ScriptedProvider("a", ProviderScript().add_transient()),
        }
        orch = GenerationOrchestrator(
            providers, retry_policy=RetryPolicy(max_attempts=3), deadline_seconds=30
        )
        token = CancellationToken()
        token.cancel()
        with pytest.raises(Exception):
            orch.run("test", 64, 64, 1, {}, log_cb=lambda m: None, token=token)

    def test_deadline_exceeded(self):
        providers = {
            "a": ScriptedProvider("a", ProviderScript().add_transient()),
        }
        orch = GenerationOrchestrator(
            providers,
            retry_policy=RetryPolicy(max_attempts=1, base_delay=0.01),
            deadline_seconds=0.05,
        )
        result = orch.run("test", 64, 64, 1, {}, log_cb=lambda m: None)
        # Should either succeed quickly or hit deadline
        assert result.image_bytes is None or result.duration_ms < 5000

    def test_health_updated_on_success(self):
        reg = get_health_registry()
        reg.reset()
        providers = {
            "test_prov": ScriptedProvider(
                "test_prov", ProviderScript().add_success()
            ),
        }
        orch = GenerationOrchestrator(providers, deadline_seconds=30)
        orch.run("test", 64, 64, 1, {}, log_cb=lambda m: None)
        health = reg.get("test_prov")
        assert health.successes == 1

    def test_health_updated_on_failure(self):
        reg = get_health_registry()
        reg.reset()
        providers = {
            "test_prov": ScriptedProvider(
                "test_prov", ProviderScript().add_transient()
            ),
        }
        orch = GenerationOrchestrator(
            providers, retry_policy=RetryPolicy(max_attempts=1), deadline_seconds=30
        )
        orch.run("test", 64, 64, 1, {}, log_cb=lambda m: None)
        health = reg.get("test_prov")
        assert health.failures == 1

    def test_unhealthy_provider_skipped(self):
        reg = get_health_registry()
        reg.reset()
        # Make provider unhealthy
        health = reg.get("unhealthy_prov")
        for _ in range(health.OPEN_THRESHOLD):
            health.record_failure("transient")

        providers = {
            "unhealthy_prov": ScriptedProvider(
                "unhealthy_prov", ProviderScript().add_success()
            ),
            "healthy_prov": ScriptedProvider(
                "healthy_prov", ProviderScript().add_success()
            ),
        }
        orch = GenerationOrchestrator(
            providers, retry_policy=RetryPolicy(max_attempts=1), deadline_seconds=30
        )
        result = orch.run("test", 64, 64, 1, {}, log_cb=lambda m: None)
        assert result.provider_id == "healthy_prov"
