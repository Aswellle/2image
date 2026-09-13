"""
tests/test_components.py — UI component library tests
"""
from __future__ import annotations

import pytest

from tests.conftest import skip_if_no_tk
from ui.components import (
    DangerButton,
    EmptyState,
    ErrorBanner,
    GhostButton,
    PrimaryButton,
    ProviderCard,
    SecondaryButton,
    StatusPill,
)
from ui.components.state_label import GenerationStateLabel
from services.generation.job_queue import JobState


@skip_if_no_tk
class TestButtons:
    def test_primary_button(self, tk_root):
        btn = PrimaryButton(tk_root, text="Test")
        assert btn.cget("text") == "Test"
        assert btn.cget("bg") != ""

    def test_secondary_button(self, tk_root):
        btn = SecondaryButton(tk_root, text="Sec")
        assert btn.cget("text") == "Sec"

    def test_danger_button(self, tk_root):
        btn = DangerButton(tk_root, text="Del")
        assert btn.cget("text") == "Del"

    def test_ghost_button(self, tk_root):
        btn = GhostButton(tk_root, text="Ghost")
        assert btn.cget("text") == "Ghost"


@skip_if_no_tk
class TestStatusPill:
    def test_info_state(self, tk_root):
        pill = StatusPill(tk_root, state="info", text="INFO")
        assert pill.cget("text") == "INFO"

    def test_success_state(self, tk_root):
        pill = StatusPill(tk_root, state="success", text="OK")
        assert pill.cget("fg") != ""


@skip_if_no_tk
class TestProviderCard:
    def test_card_creation(self, tk_root):
        card = ProviderCard(tk_root, name="Test", description="Desc", status="info")
        assert card._name_label.cget("text") == "Test"
        assert card._desc_label.cget("text") == "Desc"


@skip_if_no_tk
class TestErrorBanner:
    def test_banner_message(self, tk_root):
        banner = ErrorBanner(tk_root, message="Error occurred")
        assert banner._msg.cget("text") == "Error occurred"

    def test_set_message(self, tk_root):
        banner = ErrorBanner(tk_root, message="Initial")
        banner.set_message("Updated", level="warning")
        assert banner._msg.cget("text") == "Updated"


@skip_if_no_tk
class TestEmptyState:
    def test_empty_state(self, tk_root):
        es = EmptyState(tk_root, message="No items")
        assert es._msg.cget("text") == "No items"


@skip_if_no_tk
class TestGenerationStateLabel:
    def test_initial_state(self, tk_root):
        lbl = GenerationStateLabel(tk_root)
        assert lbl.state == JobState.QUEUED

    def test_set_state(self, tk_root):
        lbl = GenerationStateLabel(tk_root)
        lbl.set_state(JobState.SUCCEEDED)
        assert "✅" in lbl.cget("text")
        assert lbl.state == JobState.SUCCEEDED

    def test_set_state_with_provider(self, tk_root):
        lbl = GenerationStateLabel(tk_root)
        lbl.set_state(JobState.SUBMITTING, provider="SiliconFlow")
        assert "SiliconFlow" in lbl.cget("text")

    def test_set_progress(self, tk_root):
        lbl = GenerationStateLabel(tk_root)
        lbl.set_progress("Custom progress")
        assert "Custom progress" in lbl.cget("text")

    def test_set_state_from_string(self, tk_root):
        lbl = GenerationStateLabel(tk_root)
        lbl.set_state("failed")
        assert lbl.state == JobState.FAILED
