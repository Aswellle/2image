"""
ui/components/state_label.py — Generation state visualization
──────────────────────────────────────────────────────────────
Displays real-time generation progress with human-readable
state names and color coding.

Usage::

    from ui.components.state_label import GenerationStateLabel
    lbl = GenerationStateLabel(parent)
    lbl.set_state("translating")
    lbl.set_provider("SiliconFlow")
"""
from __future__ import annotations

import tkinter as tk

from config.design_tokens import TOKENS
from services.generation.job_queue import JobState


# State display config: (icon, color_key, label_key)
_STATE_DISPLAY: dict[JobState, tuple[str, str, str]] = {
    JobState.QUEUED: ("⏳", "text_secondary", "Queued"),
    JobState.TRANSLATING: ("🌐", "info", "Translating prompt…"),
    JobState.ROUTING: ("🔀", "info", "Selecting provider…"),
    JobState.SUBMITTING: ("📤", "info", "Submitting to provider…"),
    JobState.POLLING: ("⏳", "warning", "Waiting for result…"),
    JobState.DOWNLOADING: ("📥", "info", "Downloading image…"),
    JobState.VALIDATING: ("🔍", "info", "Validating image…"),
    JobState.PERSISTING: ("💾", "info", "Saving to disk…"),
    JobState.SUCCEEDED: ("✅", "success", "Generation complete"),
    JobState.FAILED: ("❌", "danger", "Generation failed"),
    JobState.CANCELLED: ("🚫", "text_muted", "Cancelled"),
    JobState.DEADLINE_EXCEEDED: ("⏰", "warning", "Deadline exceeded"),
}


class GenerationStateLabel(tk.Label):
    """Label that shows current generation state with icon and color."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            text="Ready",
            bg=TOKENS.surface_app,
            fg=TOKENS.text_secondary,
            font=("Microsoft YaHei", 11),
            anchor="w",
            **kwargs,
        )
        self._state = JobState.QUEUED
        self._provider: str | None = None

    def set_state(self, state: JobState | str, provider: str | None = None) -> None:
        """Update the displayed state."""
        if isinstance(state, str):
            state = JobState(state)
        self._state = state
        if provider:
            self._provider = provider

        icon, color_key, label = _STATE_DISPLAY.get(
            state, ("❓", "text_secondary", "Unknown")
        )
        color = getattr(TOKENS, color_key, TOKENS.text_secondary)

        provider_text = f" ({self._provider})" if self._provider else ""
        self.config(text=f"{icon} {label}{provider_text}", fg=color)

    def set_progress(self, message: str, color_key: str = "info") -> None:
        """Set a custom progress message."""
        color = getattr(TOKENS, color_key, TOKENS.text_secondary)
        provider_text = f" ({self._provider})" if self._provider else ""
        self.config(text=f"⏳ {message}{provider_text}", fg=color)

    @property
    def state(self) -> JobState:
        return self._state
