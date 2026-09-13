"""
services/application/menu_controller.py — Menu building controller
─────────────────────────────────────────────────────────────────────
Extracts menu construction from App._build_menu() to slim down
the main window class.
"""
from __future__ import annotations

import os
import webbrowser
from tkinter import Menu



from config.settings import APP_DIR, LOG_FILE
from config.theme import DARK_THEME as C
from config.i18n import _


class MenuController:
    """Builds and manages the application menu bar."""

    def __init__(self, app) -> None:
        self.app = app
        self.root = app.root

    def build(self) -> None:
        """Build the complete menu bar."""
        menubar = Menu(self.root, bg=C["panel"], fg=C["text"],
                       activebackground=C["acc"], activeforeground="white",
                       relief="flat", bd=0)
        self.root.config(menu=menubar)

        self._build_tools_menu(menubar)
        self._build_api_menu(menubar)
        self._build_data_menu(menubar)
        self._build_settings_menu(menubar)

    def _menu(self, parent) -> Menu:
        return Menu(parent, tearoff=0,
                    bg=C["panel"], fg=C["text"],
                    activebackground=C["acc"], activeforeground="white",
                    relief="flat", bd=0)

    def _open_url(self, url: str):
        return lambda: webbrowser.open(url)

    def _build_tools_menu(self, menubar: Menu) -> None:
        m_tools = self._menu(menubar)
        menubar.add_cascade(label=_("menu_tools"), menu=m_tools)
        m_tools.add_command(label=_("wizard_title") + "…        Ctrl+P",
                            command=self.app._open_prompt_wizard)
        m_tools.add_separator()
        m_tools.add_command(label=_("phrase_title") + "…         Ctrl+B",
                            command=self.app._open_phrase_panel)
        m_tools.add_command(label=_("btn_variant_gen"),
                            command=self.app._switch_to_variant_tab)
        m_tools.add_command(label="  📋  " + _("tab_queue").strip() + "…         Ctrl+Q",
                            command=self.app._switch_to_queue_tab)

    def _build_api_menu(self, menubar: Menu) -> None:
        m_api = self._menu(menubar)
        menubar.add_cascade(label=" 🔑  接口配置 ", menu=m_api)
        m_api.add_command(label="  🆓  免费接口配置…", command=self.app._open_wizard)
        m_api.add_command(label="  💎  付费接口配置…", command=self.app._open_paid_wizard)
        m_api.add_separator()

        # Free provider registration links
        m_free_links = self._menu(m_api)
        m_api.add_cascade(label="  🌐  免费接口注册链接", menu=m_free_links)
        m_free_links.add_command(label="  ★  硅基流动（推荐，免费赠额）",
            command=self._open_url("https://cloud.siliconflow.cn/account/ak"))
        m_free_links.add_command(label="  ·  Google Gemini（500次/天）",
            command=self._open_url("https://aistudio.google.com/app/apikey"))
        m_free_links.add_command(label="  ·  Cloudflare AI（1万次/天）",
            command=self._open_url("https://dash.cloudflare.com/profile/api-tokens"))
        m_free_links.add_command(label="  ·  OpenRouter（部分模型免费）",
            command=self._open_url("https://openrouter.ai/keys"))
        m_free_links.add_command(label="  ·  ModelsLab（100次/天）",
            command=self._open_url("https://modelslab.com/dashboard/api"))
        m_free_links.add_command(label="  ·  Segmind（注册送 $5）",
            command=self._open_url("https://www.segmind.com/"))
        m_free_links.add_command(label="  ·  HuggingFace Token",
            command=self._open_url("https://huggingface.co/settings/tokens/new?tokenType=read"))

        # Paid provider registration links
        m_paid_links = self._menu(m_api)
        m_api.add_cascade(label="  🌐  付费接口注册链接", menu=m_paid_links)
        m_paid_links.add_command(label="  ·  OpenAI GPT-Image",
            command=self._open_url("https://platform.openai.com/api-keys"))
        m_paid_links.add_command(label="  ·  Stability AI",
            command=self._open_url("https://platform.stability.ai/"))
        m_paid_links.add_command(label="  ·  Replicate FLUX",
            command=self._open_url("https://replicate.com/account/api-tokens"))
        m_paid_links.add_command(label="  ·  xAI Grok（注册送 $25）",
            command=self._open_url("https://console.x.ai/"))

    def _build_data_menu(self, menubar: Menu) -> None:
        m_data = self._menu(menubar)
        menubar.add_cascade(label=_("menu_data"), menu=m_data)
        m_data.add_command(label="  📊  统计看板…", command=self.app._show_stats)
        m_data.add_separator()

        def _open_path(p: str) -> None:
            if os.name == "nt":
                os.startfile(p)
            else:
                import subprocess as _sp
                _sp.Popen(["xdg-open", p])

        m_data.add_command(label="  📁  数据文件夹",
            command=lambda: _open_path(APP_DIR))
        m_data.add_command(label="  📄  调试日志",
            command=lambda: _open_path(LOG_FILE))

    def _build_settings_menu(self, menubar: Menu) -> None:
        m_set = self._menu(menubar)
        menubar.add_cascade(label=_("menu_settings"), menu=m_set)
        m_set.add_command(label="  🖼  应用偏好设置…", command=self.app._open_app_settings)
        m_set.add_command(label="  ⌨  快捷键说明…", command=self.app._show_shortcuts)
