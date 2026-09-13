"""
tests/fakes/__init__.y — Fault injection test harness
────────────────────────────────────────────────────
Provides scriptable fake providers, HTTP mocks, and clocks
for deterministic testing of orchestrator/router/retry/health
without any network access.
"""
from tests.fakes.fake_provider import ScriptedProvider, ProviderScript
from tests.fakes.fake_http import FakeResponse, FakeSession

__all__ = ["ScriptedProvider", "ProviderScript", "FakeResponse", "FakeSession"]
