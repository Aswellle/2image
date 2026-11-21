"""
services/application/settings_controller.py — Settings window controller
─────────────────────────────────────────────────────────────────────────
Language persistence stays here (pure business logic); the settings /
shortcuts windows themselves live in ui/settings_windows.py — the
services layer must not import tkinter to build UI (layering: ui →
services is one-way).
"""

from __future__ import annotations

from config.settings import save_config
from config.i18n import _


class SettingsController:
    """Manages application settings windows."""

    def __init__(self, app) -> None:
        self.app = app
        self.root = app.root

    def set_language(self, lang: str) -> None:
        """保存界面语言选择（重启应用后由 init_language 生效）。"""
        if lang not in self.app.SUPPORTED_LANGUAGES:
            return
        if lang == self.app.cfg.get("language", "zh-CN"):
            return
        self.app.cfg["language"] = lang
        save_config(self.app.cfg)
        self.app._toast(_("settings_lang_restart"), "info")
        self.app._log(f"🌐 language → {lang} (restart to apply)")

    def show_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog."""
        from ui.settings_windows import ShortcutsWindow

        ShortcutsWindow(self.app)

    def show_app_settings(self) -> None:
        """Show application preferences dialog."""
        from ui.settings_windows import AppSettingsWindow

        AppSettingsWindow(self.app)
