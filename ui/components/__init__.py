"""
ui/components/__init__.py — Reusable UI component library

Standardized widgets that consume design tokens for visual
consistency.  All components accept standard tkinter kwargs
plus token-driven styling.

Usage::

    from ui.components import PrimaryButton, ProviderCard, StatusPill
    btn = PrimaryButton(parent, text="Generate", command=on_click)
    pill = StatusPill(parent, state="success", text="Connected")
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from config.design_tokens import TOKENS, button_colors, status_pill_colors


class PrimaryButton(tk.Button):
    """Primary action button with token-driven styling."""

    def __init__(
        self,
        master,
        text: str = "",
        command: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        colors = button_colors("normal", "primary")
        super().__init__(
            master,
            text=text,
            command=command,
            bg=colors["bg"],
            fg=colors["fg"],
            activebackground=TOKENS.highlight,
            activeforeground=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_md, "bold"),
            bd=0,
            padx=TOKENS.space_lg,
            pady=TOKENS.space_sm,
            cursor="hand2",
            **kwargs,
        )


class SecondaryButton(tk.Button):
    """Secondary action button."""

    def __init__(
        self,
        master,
        text: str = "",
        command: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        colors = button_colors("normal", "secondary")
        super().__init__(
            master,
            text=text,
            command=command,
            bg=colors["bg"],
            fg=colors["fg"],
            activebackground=TOKENS.accent,
            activeforeground=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_md),
            bd=0,
            padx=TOKENS.space_md,
            pady=TOKENS.space_sm,
            cursor="hand2",
            **kwargs,
        )


class DangerButton(tk.Button):
    """Danger/destructive action button."""

    def __init__(
        self,
        master,
        text: str = "",
        command: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        colors = button_colors("normal", "danger")
        super().__init__(
            master,
            text=text,
            command=command,
            bg=colors["bg"],
            fg=colors["fg"],
            activebackground=TOKENS.highlight,
            activeforeground=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_md),
            bd=0,
            padx=TOKENS.space_md,
            pady=TOKENS.space_sm,
            cursor="hand2",
            **kwargs,
        )


class GhostButton(tk.Button):
    """Minimal/ghost button."""

    def __init__(
        self,
        master,
        text: str = "",
        command=None,
        **kwargs,
    ) -> None:
        colors = button_colors("normal", "ghost")
        bg = colors["bg"] if colors["bg"] != "transparent" else TOKENS.surface_panel
        super().__init__(
            master,
            text=text,
            command=command,
            bg=bg,
            fg=colors["fg"],
            activebackground=TOKENS.surface_elevated,
            activeforeground=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_sm),
            bd=0,
            padx=TOKENS.space_sm,
            pady=TOKENS.space_xs,
            cursor="hand2",
            **kwargs,
        )


class StatusPill(tk.Label):
    """Small status indicator pill."""

    def __init__(
        self,
        master,
        state: str = "info",
        text: str = "",
        **kwargs,
    ) -> None:
        colors = status_pill_colors(state)
        super().__init__(
            master,
            text=text,
            bg=colors["bg"],
            fg=colors["fg"],
            font=(TOKENS.font_family, TOKENS.font_size_xs, "bold"),
            padx=TOKENS.space_sm,
            pady=2,
            **kwargs,
        )


class ProviderCard(tk.Frame):
    """Card widget for displaying provider info."""

    def __init__(
        self,
        master,
        name: str = "",
        description: str = "",
        status: str = "info",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            bg=TOKENS.surface_panel,
            highlightbackground=TOKENS.border_subtle,
            highlightthickness=1,
            **kwargs,
        )
        # Name label
        self._name_label = tk.Label(
            self,
            text=name,
            bg=TOKENS.surface_panel,
            fg=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_md, "bold"),
            anchor="w",
        )
        self._name_label.pack(fill="x", padx=TOKENS.space_md, pady=(TOKENS.space_sm, 0))

        # Description
        self._desc_label = tk.Label(
            self,
            text=description,
            bg=TOKENS.surface_panel,
            fg=TOKENS.text_secondary,
            font=(TOKENS.font_family, TOKENS.font_size_sm),
            anchor="w",
        )
        self._desc_label.pack(fill="x", padx=TOKENS.space_md)

        # Status pill
        self._status_pill = StatusPill(self, state=status, text=status.upper())
        self._status_pill.pack(anchor="w", padx=TOKENS.space_md, pady=TOKENS.space_sm)


class ErrorBanner(tk.Frame):
    """Error/info banner for displaying messages."""

    def __init__(
        self,
        master,
        message: str = "",
        level: str = "danger",
        **kwargs,
    ) -> None:
        color = TOKENS.danger if level == "danger" else (
            TOKENS.warning if level == "warning" else TOKENS.info
        )
        super().__init__(
            master,
            bg=TOKENS.surface_elevated,
            highlightbackground=color,
            highlightthickness=1,
            **kwargs,
        )
        self._icon = tk.Label(
            self,
            text="⚠" if level != "info" else "ℹ",
            bg=TOKENS.surface_elevated,
            fg=color,
            font=(TOKENS.font_family, TOKENS.font_size_lg),
        )
        self._icon.pack(side="left", padx=TOKENS.space_sm)

        self._msg = tk.Label(
            self,
            text=message,
            bg=TOKENS.surface_elevated,
            fg=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_sm),
            anchor="w",
        )
        self._msg.pack(side="left", fill="x", expand=True, padx=TOKENS.space_xs)

    def set_message(self, message: str, level: str = "danger") -> None:
        color = TOKENS.danger if level == "danger" else (
            TOKENS.warning if level == "warning" else TOKENS.info
        )
        self._msg.config(text=message)
        self._icon.config(text="⚠" if level != "info" else "ℹ", fg=color)


class EmptyState(tk.Frame):
    """Empty state placeholder."""

    def __init__(
        self,
        master,
        message: str = "No items",
        **kwargs,
    ) -> None:
        super().__init__(master, bg=TOKENS.surface_app, **kwargs)
        self._icon = tk.Label(
            self,
            text="📭",
            bg=TOKENS.surface_app,
            fg=TOKENS.text_muted,
            font=(TOKENS.font_family, TOKENS.font_size_2xl),
        )
        self._icon.pack(pady=TOKENS.space_xl)

        self._msg = tk.Label(
            self,
            text=message,
            bg=TOKENS.surface_app,
            fg=TOKENS.text_muted,
            font=(TOKENS.font_family, TOKENS.font_size_md),
        )
        self._msg.pack()


class LoadingIndicator(tk.Frame):
    """Animated loading indicator."""

    def __init__(
        self,
        master,
        text: str = "Loading...",
        **kwargs,
    ) -> None:
        super().__init__(master, bg=TOKENS.surface_app, **kwargs)
        self._label = tk.Label(
            self,
            text=text,
            bg=TOKENS.surface_app,
            fg=TOKENS.text_secondary,
            font=(TOKENS.font_family, TOKENS.font_size_sm),
        )
        self._label.pack()
        self._dots = 0
        self._after_id = None

from ui.components.state_label import GenerationStateLabel

__all__ = [
    "PrimaryButton",
    "SecondaryButton",
    "DangerButton",
    "GhostButton",
    "StatusPill",
    "ProviderCard",
    "ErrorBanner",
    "EmptyState",
    "LoadingIndicator",
    "GenerationStateLabel",
]


