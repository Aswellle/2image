"""
tests/fakes/scenarios.py — Pre-built fault injection scenarios
──────────────────────────────────────────────────────────────
Reusable test scenarios for common provider failure patterns.
"""
from __future__ import annotations

from tests.fakes.fake_http import FakeResponse, FakeSession, make_image_response
from tests.fakes.fake_provider import ProviderScript, ScriptedProvider



def scenario_then_fallback(
    failing_id: str = "provider_a",
    success_id: str = "provider_b",
) -> dict[str, ScriptedProvider]:
    """First provider times out, second succeeds."""
    return {
        failing_id: ScriptedProvider(
            failing_id,
            ProviderScript().add_transient("timeout"),
        ),
        success_id: ScriptedProvider(
            success_id,
            ProviderScript().add_success(),
        ),
    }


def scenario_auth_then_stop(
    bad_id: str = "openai",
) -> dict[str, ScriptedProvider]:
    """Auth error on one provider — orchestrator must NOT keep trying."""
    return {
        bad_id: ScriptedProvider(
            bad_id,
            ProviderScript().add_auth_failure(),
        ),
    }


def scenario_rate_limit_then_success(
    limited_id: str = "gemini",
    success_id: str = "siliconflow",
) -> dict[str, ScriptedProvider]:
    """429 with Retry-After, then fallback succeeds."""
    return {
        limited_id: ScriptedProvider(
            limited_id,
            ProviderScript().add_rate_limit(retry_after=1.0),
        ),
        success_id: ScriptedProvider(
            success_id,
            ProviderScript().add_success(),
        ),
    }


def scenario_all_fail(ids: list[str] | None = None) -> dict[str, ScriptedProvider]:
    """Every provider fails — orchestrator raises after exhausting all."""
    ids = ids or ["a", "b", "c"]
    return {
        pid: ScriptedProvider(pid, ProviderScript().add_transient("down"))
        for pid in ids
    }


def scenario_recovery_after_transients(
    provider_id: str = "pollinations",
    fail_count: int = 2,
) -> dict[str, ScriptedProvider]:
    """Provider fails N times then recovers."""
    script = ProviderScript()
    for _ in range(fail_count):
        script.add_transient("intermittent")
    script.add_success()
    return {provider_id: ScriptedProvider(provider_id, script)}


def http_scenario_429_then_200() -> FakeSession:
    """Fake session that returns 429 then 200."""
    session = FakeSession()
    session.enqueue(
        FakeResponse(status_code=429, headers={"Retry-After": "1"}, content=b"slow down")
    )
    session.enqueue(make_image_response())
    return session


def http_scenario_500_sequence(count: int = 3) -> FakeSession:
    """Fake session that returns N 500 errors."""
    session = FakeSession()
    for _ in range(count):
        session.enqueue(FakeResponse(status_code=503, content=b"service unavailable"))
    return session


def http_scenario_connection_error() -> FakeSession:
    """Fake session that raises ConnectionError."""
    session = FakeSession()
    session.enqueue(ConnectionError("Connection refused"))
    return session
