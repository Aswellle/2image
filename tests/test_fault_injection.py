"""
tests/test_fault_injection.py — Provider fault injection suite
─────────────────────────────────────────────────────────────
Validates error taxonomy, retry behavior, cancellation,
and circuit breaker using scripted fake providers — no network.
"""
from __future__ import annotations

import pytest

from services.generation.cancellation import CancellationToken, Deadline
from services.generation.errors import (
    DeadlineExceeded,
    GenerationCancelled,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderPolicyError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderTransientError,
    classify_http_error,
)
from services.generation.retry_policy import RetryPolicy, get_retry_policy
from tests.fakes.fake_http import FakeResponse, FakeSession, make_image_response
from tests.fakes.fake_provider import ProviderScript, ScriptedProvider
from tests.fakes.scenarios import (
    http_scenario_429_then_200,
    scenario_all_fail,
    scenario_auth_then_stop,

    scenario_recovery_after_transients,
    scenario_then_fallback,
)


# ─── Error Taxonomy Tests ─────────────────────────────────────────


class TestErrorTaxonomy:
    """Verify error classification and flags."""

    def test_auth_error_not_retryable(self):
        err = ProviderAuthError("bad key")
        assert err.retryable is False
        assert err.fallback is False
        assert err.code == "auth_failed"

    def test_quota_error_fallback_not_retryable(self):
        err = ProviderQuotaError("no quota")
        assert err.retryable is False
        assert err.fallback is True
        assert err.code == "quota_exhausted"

    def test_rate_limit_retryable_with_retry_after(self):
        err = ProviderRateLimitError("slow", retry_after=2.5)
        assert err.retryable is True
        assert err.fallback is True
        assert err.retry_after == 2.5
        assert err.code == "rate_limited"

    def test_transient_retryable(self):
        err = ProviderTransientError("timeout")
        assert err.retryable is True
        assert err.fallback is True
        assert err.code == "transient"

    def test_invalid_request_not_retryable(self):
        err = ProviderInvalidRequestError("bad params")
        assert err.retryable is False
        assert err.fallback is False

    def test_policy_error_fallback_no_retry(self):
        err = ProviderPolicyError("rejected")
        assert err.retryable is False
        assert err.fallback is True

    def test_base_provider_error_defaults(self):
        err = ProviderError("generic")
        assert err.retryable is False
        assert err.fallback is True
        assert err.code == "provider_error"


class TestHTTPErrorClassification:
    """Verify HTTP status → domain error mapping."""

    @pytest.mark.parametrize(
        "status,expected_type",
        [
            (400, ProviderInvalidRequestError),
            (401, ProviderAuthError),
            (402, ProviderQuotaError),
            (403, ProviderAuthError),
            (404, ProviderAuthError),
            (408, ProviderTransientError),
            (422, ProviderInvalidRequestError),
            (429, ProviderRateLimitError),
            (500, ProviderTransientError),
            (502, ProviderTransientError),
            (503, ProviderTransientError),
            (504, ProviderTransientError),
        ],
    )
    def test_http_status_maps_to_domain_error(self, status, expected_type):
        err = classify_http_error(status)
        assert isinstance(err, expected_type)

    def test_429_preserves_retry_after(self):
        err = classify_http_error(429, "rate limited")
        assert isinstance(err, ProviderRateLimitError)
        assert err.retryable is True

    def test_unknown_4xx_maps_to_invalid_request(self):
        err = classify_http_error(418)
        assert isinstance(err, ProviderInvalidRequestError)

    def test_unknown_5xx_maps_to_transient(self):
        err = classify_http_error(520)
        assert isinstance(err, ProviderTransientError)


# ─── CancellationToken Tests ───────────────────────────────────────


class TestCancellationToken:
    def test_initially_not_cancelled(self):
        token = CancellationToken()
        assert token.is_cancelled() is False

    def test_cancel_sets_flag(self):
        token = CancellationToken()
        token.cancel()
        assert token.is_cancelled() is True

    def test_throw_if_cancelled_raises(self):
        token = CancellationToken()
        token.cancel()
        with pytest.raises(GenerationCancelled):
            token.throw_if_cancelled()

    def test_throw_if_not_cancelled_passes(self):
        token = CancellationToken()
        token.throw_if_cancelled()  # should not raise

    def test_wait_returns_true_when_cancelled(self):
        token = CancellationToken()
        token.cancel()
        result = token.wait(10.0)
        assert result is True


class TestDeadline:
    def test_not_expired_immediately(self):
        dl = Deadline(seconds=60.0)
        assert dl.is_expired() is False
        assert dl.remaining() > 0

    def test_expired_after_timeout(self):
        dl = Deadline(seconds=0.05)
        import time
        time.sleep(0.2)
        assert dl.is_expired() is True

    def test_assert_alive_raises_when_expired(self):
        dl = Deadline(seconds=0.01)
        import time
        time.sleep(0.15)
        with pytest.raises(DeadlineExceeded):
            dl.assert_alive()

    def test_remaining_decreases(self):
        dl = Deadline(seconds=10.0)
        r1 = dl.remaining()
        import time
        time.sleep(0.1)
        r2 = dl.remaining()
        assert r2 < r1




# ─── RetryPolicy Tests ────────────────────────────────────────────


class TestRetryPolicy:
    def test_delay_increases_with_attempt(self):
        policy = RetryPolicy(base_delay=1.0, jitter=0.0)
        d1 = policy.delay(1)
        d2 = policy.delay(2)
        d3 = policy.delay(3)
        assert d1 < d2 < d3

    def test_delay_respects_max(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=5.0, jitter=0.0)
        d = policy.delay(10)  # would be 512 without cap
        assert d <= 5.0

    def test_retry_after_overrides_backoff(self):
        policy = RetryPolicy(base_delay=1.0, jitter=0.0)
        d = policy.delay(1, retry_after=3.0)
        assert d == 3.0

    def test_retry_after_capped_at_max(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=2.0, jitter=0.0)
        d = policy.delay(1, retry_after=10.0)
        assert d == 2.0

    def test_max_attempts_at_least_one(self):
        policy = RetryPolicy(max_attempts=0)
        assert policy.max_attempts == 1

    def test_get_named_policy(self):
        policy = get_retry_policy("conservative")
        assert policy.max_attempts == 2

    def test_unknown_policy_returns_default(self):
        policy = get_retry_policy("nonexistent")
        assert policy.max_attempts == 3  # default


# ─── Fake Provider Tests ──────────────────────────────────────────


class TestScriptedProvider:
    def test_success_returns_bytes_and_id(self):
        script = ProviderScript().add_success(latency_ms=50)
        provider = ScriptedProvider("test", script)
        data, used = provider.generate("prompt", 1024, 1024, 42, {}, lambda m: None)
        assert data.startswith(b"\x89PNG")
        assert used == "test"
        assert provider.call_count == 1

    def test_error_raises_scripted_exception(self):
        script = ProviderScript().add_auth_failure()
        provider = ScriptedProvider("test", script)
        with pytest.raises(ProviderAuthError):
            provider.generate("prompt", 1024, 1024, 42, {}, lambda m: None)

    def test_exhausted_script_raises(self):
        script = ProviderScript().add_success()
        provider = ScriptedProvider("test", script)
        provider.generate("prompt", 1024, 1024, 42, {}, lambda m: None)
        with pytest.raises(RuntimeError, match="Script exhausted"):
            provider.generate("prompt", 1024, 1024, 42, {}, lambda m: None)

    def test_call_count_tracks_invocations(self):
        script = ProviderScript()
        script.add_transient()
        script.add_success()
        provider = ScriptedProvider("test", script)
        try:
            provider.generate("p", 1, 1, 1, {}, lambda m: None)
        except Exception:
            pass
        provider.generate("p", 1, 1, 1, {}, lambda m: None)
        assert provider.call_count == 2


# ─── Fake HTTP Tests ──────────────────────────────────────────────


class TestFakeHTTP:
    def test_default_response(self):
        session = FakeSession()
        resp = session.get("https://example.com")
        assert resp.status_code == 200

    def test_queued_response(self):
        session = FakeSession()
        session.enqueue(FakeResponse(status_code=429))
        resp = session.get("https://example.com")
        assert resp.status_code == 429

    def test_queued_exception(self):
        session = FakeSession()
        session.enqueue(ConnectionError("refused"))
        with pytest.raises(ConnectionError):
            session.get("https://example.com")

    def test_request_recording(self):
        session = FakeSession()
        session.get("https://a.com", timeout=5)
        session.post("https://b.com", json={"x": 1})
        assert len(session.requests) == 2
        assert session.requests[0]["method"] == "GET"
        assert session.requests[1]["method"] == "POST"

    def test_raise_for_status(self):
        resp = FakeResponse(status_code=500)
        with pytest.raises(Exception):
            resp.raise_for_status()

    def test_make_image_response_valid_png(self):
        resp = make_image_response(width=32, height=32, fmt="png")
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "image/png"
        assert resp.content[:4] == b"\x89PNG"

    def test_iter_content_chunks(self):
        resp = FakeResponse(content=b"Hello World" * 100)
        chunks = list(resp.iter_content(chunk_size=50))
        assert b"".join(chunks) == b"Hello World" * 100

    def test_iter_content_empty(self):
        resp = FakeResponse(content=b"")
        chunks = list(resp.iter_content())
        assert chunks == [b""]


# ─── Scenario Tests ───────────────────────────────────────────────


class TestScenarios:
    def test_then_fallback(self):
        providers = scenario_then_fallback("a", "b")
        assert "a" in providers
        assert "b" in providers
        # First provider should fail
        with pytest.raises(ProviderTransientError):
            providers["a"].generate("p", 1, 1, 1, {}, lambda m: None)
        # Second should succeed
        data, _ = providers["b"].generate("p", 1, 1, 1, {}, lambda m: None)
        assert data.startswith(b"\x89PNG")

    def test_auth_then_stop(self):
        providers = scenario_auth_then_stop("openai")
        with pytest.raises(ProviderAuthError):
            providers["openai"].generate("p", 1, 1, 1, {}, lambda m: None)

    def test_all_fail(self):
        providers = scenario_all_fail(["x", "y"])
        for p in providers.values():
            with pytest.raises(ProviderTransientError):
                p.generate("p", 1, 1, 1, {}, lambda m: None)

    def test_recovery_after_transients(self):
        providers = scenario_recovery_after_transients("p", fail_count=2)
        with pytest.raises(ProviderTransientError):
            providers["p"].generate("p", 1, 1, 1, {}, lambda m: None)
        with pytest.raises(ProviderTransientError):
            providers["p"].generate("p", 1, 1, 1, {}, lambda m: None)
        data, _ = providers["p"].generate("p", 1, 1, 1, {}, lambda m: None)
        assert data.startswith(b"\x89PNG")

    def test_http_429_then_200(self):
        session = http_scenario_429_then_200()
        r1 = session.get("https://api.example.com/generate")
        assert r1.status_code == 429
        r2 = session.get("https://api.example.com/generate")
        assert r2.status_code == 200
        assert r2.content[:4] == b"\x89PNG"
