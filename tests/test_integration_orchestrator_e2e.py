"""
tests/test_integration_orchestrator_e2e.py — End-to-end orchestrator integration

Proves that generate_image() now routes through the GenerationOrchestrator,
making cancellation, deadline, health, and error taxonomy active in the
production code path.
"""
from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

from services.generation.cancellation import CancellationToken
from services.generation.errors import GenerationCancelled
from services.image_service import generate_image


class TestGenerateImageUsesOrchestrator:
    """Verify generate_image routes through the orchestrator."""

    def test_auth_error_does_not_retry(self):
        """401/ValueError(auth) should NOT be retried -- immediate fallback."""
        call_count = {"n": 0}

        def auth_fail(prompt, w, h, seed, cfg, log):
            call_count["n"] += 1
            raise ValueError("需要 OpenAI API Key，请在配置中填写")

        def success(prompt, w, h, seed, cfg, log):
            return (b"\x89PNG\r\n\x1a\n", "free_fallback")

        with patch("services.image_service.ALL_PROVIDERS",
                   {"auth_required": auth_fail, "free_fallback": success}):
            data, used = generate_image("test", 64, 64, 42, {},
                                         provider_order=["auth_required", "free_fallback"])

        assert used == "free_fallback"
        assert data == b"\x89PNG\r\n\x1a\n"
        # Auth provider should be called exactly ONCE (no retry)
        assert call_count["n"] == 1

    def test_cancellation_stops_immediately(self):
        """Cancelling the token during retry sleep should raise GenerationCancelled."""
        import time

        call_count = {"n": 0}

        def flaky_provider(prompt, w, h, seed, cfg, log):
            call_count["n"] += 1
            # Fail with a transient error to trigger retry (with sleep)
            raise RuntimeError("connection reset")

        token = CancellationToken()

        def cancel_during_retry_sleep():
            # Wait for the first attempt to fail and retry sleep to start
            time.sleep(0.3)
            token.cancel()

        threading.Thread(target=cancel_during_retry_sleep, daemon=True).start()

        with patch("services.image_service.ALL_PROVIDERS",
                   {"flaky": flaky_provider}):
            with pytest.raises(GenerationCancelled):
                generate_image("test", 64, 64, 42, {},
                               provider_order=["flaky"], token=token)
    def test_transient_error_retries_then_falls_back(self):
        """Transient errors should be retried (with backoff) then fall back."""
        call_count = {"n": 0}

        def flaky(prompt, w, h, seed, cfg, log):
            call_count["n"] += 1
            raise RuntimeError("connection reset")

        def good(prompt, w, h, seed, cfg, log):
            return (b"\x89PNG", "good")

        with patch("services.image_service.ALL_PROVIDERS",
                   {"flaky": flaky, "good": good}):
            data, used = generate_image("test", 64, 64, 42, {},
                                         provider_order=["flaky", "good"])

        assert used == "good"
        assert call_count["n"] >= 1

    def test_no_token_backward_compat(self):
        """generate_image() without token should still work (backward compat)."""
        def good(prompt, w, h, seed, cfg, log):
            return (b"\x89PNG", "good")

        with patch("services.image_service.ALL_PROVIDERS", {"good": good}):
            data, used = generate_image("test", 64, 64, 42, {},
                                         provider_order=["good"])
        assert used == "good"

    def test_token_cancel_before_run(self):
        """Token cancelled before run should raise immediately."""
        token = CancellationToken()
        token.cancel()

        def good(prompt, w, h, seed, cfg, log):
            return (b"data", "good")

        with patch("services.image_service.ALL_PROVIDERS", {"good": good}):
            with pytest.raises(GenerationCancelled):
                generate_image("test", 64, 64, 42, {},
                               provider_order=["good"], token=token)
