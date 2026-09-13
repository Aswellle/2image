"""
config/design_tokens.py — Semantic design tokens
─────────────────────────────────────────────────
Central design system with semantic color names, spacing,
typography scale, and component states.  Replaces hardcoded
colors throughout the UI files.

Usage::

    from config.design_tokens import TOKENS
    label.config(bg=TOKENS["surface_panel"], fg=TOKENS["text_primary"])
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DesignTokens:
    """Semantic design token system."""

    # Surface hierarchy
    surface_app: str = "#0a0f1a"
    surface_panel: str = "#0d1b2a"
    surface_elevated: str = "#142238"
    surface_overlay: str = "#1a2d4a"

    # Text colors
    text_primary: str = "#eaeaea"
    text_secondary: str = "#a0b0c0"
    text_muted: str = "#7a8aaa"
    text_inverse: str = "#0a0f1a"

    # Accent & state
    accent: str = "#1e3a6a"
    accent_hover: str = "#2a4f8a"
    highlight: str = "#e94560"

    # Semantic colors
    success: str = "#4ecca3"
    warning: str = "#f0a500"
    danger: str = "#e94560"
    info: str = "#4a90d9"

    # Borders & dividers
    border_subtle: str = "#1e2d4a"
    border_focus: str = "#2a4f8a"

    # Spacing scale (px)
    space_xs: int = 4
    space_sm: int = 8
    space_md: int = 12
    space_lg: int = 16
    space_xl: int = 24
    space_2xl: int = 32

    # Border radius
    radius_sm: int = 4
    radius_md: int = 8
    radius_lg: int = 12
    radius_round: int = 9999

    # Typography
    font_family: str = "Microsoft YaHei"
    font_family_mono: str = "Consolas"
    font_size_xs: int = 10
    font_size_sm: int = 11
    font_size_md: int = 13
    font_size_lg: int = 16
    font_size_xl: int = 20
    font_size_2xl: int = 28

    # Shadows (tkinter doesn't support real shadows, but we can use for canvas)
    shadow_color: str = "#000000"

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


# Light theme variant
LIGHT_TOKENS = DesignTokens(
    surface_app="#f5f7fa",
    surface_panel="#ffffff",
    surface_elevated="#e8ecf0",
    surface_overlay="#dfe4ea",
    text_primary="#1a1a2e",
    text_secondary="#4a5568",
    text_muted="#718096",
    text_inverse="#ffffff",
    accent="#3182ce",
    accent_hover="#2c5282",
    highlight="#e53e3e",
    success="#38a169",
    warning="#d69e2e",
    danger="#e53e3e",
    info="#3182ce",
    border_subtle="#e2e8f0",
    border_focus="#3182ce",
)

# Default dark theme
TOKENS = DesignTokens()


# ─── Button state helpers ─────────────────────────────────────────

def button_colors(state: str = "normal", variant: str = "primary") -> dict:
    """
    Get button colors for a given state and variant.

    States: normal, hover, pressed, disabled, loading
    Variants: primary, secondary, ghost, danger
    """
    if variant == "primary":
        return {
            "normal": {"bg": TOKENS.accent, "fg": TOKENS.text_primary},
            "hover": {"bg": TOKENS.accent_hover, "fg": TOKENS.text_primary},
            "pressed": {"bg": TOKENS.highlight, "fg": TOKENS.text_primary},
            "disabled": {"bg": TOKENS.surface_elevated, "fg": TOKENS.text_muted},
            "loading": {"bg": TOKENS.accent, "fg": TOKENS.text_muted},
        }.get(state, {"bg": TOKENS.accent, "fg": TOKENS.text_primary})

    if variant == "secondary":
        return {
            "normal": {"bg": TOKENS.surface_elevated, "fg": TOKENS.text_primary},
            "hover": {"bg": TOKENS.border_subtle, "fg": TOKENS.text_primary},
            "pressed": {"bg": TOKENS.accent, "fg": TOKENS.text_primary},
            "disabled": {"bg": TOKENS.surface_panel, "fg": TOKENS.text_muted},
        }.get(state, {"bg": TOKENS.surface_elevated, "fg": TOKENS.text_primary})

    if variant == "danger":
        return {
            "normal": {"bg": TOKENS.danger, "fg": TOKENS.text_primary},
            "hover": {"bg": TOKENS.highlight, "fg": TOKENS.text_primary},
            "pressed": {"bg": TOKENS.highlight, "fg": TOKENS.text_inverse},
            "disabled": {"bg": TOKENS.surface_elevated, "fg": TOKENS.text_muted},
        }.get(state, {"bg": TOKENS.danger, "fg": TOKENS.text_primary})

    # ghost
    return {
        "normal": {"bg": "transparent", "fg": TOKENS.text_primary},
        "hover": {"bg": TOKENS.surface_elevated, "fg": TOKENS.text_primary},
        "pressed": {"bg": TOKENS.accent, "fg": TOKENS.text_primary},
        "disabled": {"bg": "transparent", "fg": TOKENS.text_muted},
    }.get(state, {"bg": "transparent", "fg": TOKENS.text_primary})


def status_pill_colors(state: str = "info") -> dict:
    """Get status pill colors: info, success, warning, danger."""
    return {
        "info": {"bg": TOKENS.info, "fg": TOKENS.text_inverse},
        "success": {"bg": TOKENS.success, "fg": TOKENS.text_inverse},
        "warning": {"bg": TOKENS.warning, "fg": TOKENS.text_inverse},
        "danger": {"bg": TOKENS.danger, "fg": TOKENS.text_inverse},
    }.get(state, {"bg": TOKENS.info, "fg": TOKENS.text_inverse})
