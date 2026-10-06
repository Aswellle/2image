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
        """Build the complete menu bar.

        结构（§66 信息层级）：
            文件   — 文档/图片级动作（查看器、另存为、导出、日志）
            工具   — 创作辅助（提示词助手、词库、结果 Tab）
            接口   — 供应商配置与注册链接
            数据   — 统计与本地数据入口
            设置   — 界面语言、偏好、快捷键
        """
        menubar = Menu(self.root, tearoff=0,
                       bg=C["panel"], fg=C["text"],
                       activebackground=C["acc"], activeforeground="white",
                       relief="flat", bd=0)
        self.root.config(menu=menubar)

        self._build_file_menu(menubar)
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

    def _build_file_menu(self, menubar: Menu) -> None:
        m_file = self._menu(menubar)
        menubar.add_cascade(label=_("menu_file"), menu=m_file)
        m_file.add_command(label=_("menu_open_viewer") + "   Ctrl+O",
                           command=self.app._open_viewer)
        m_file.add_command(label=_("menu_save_as") + "   Ctrl+S",
                           command=self.app._save)
        m_file.add_command(label=_("menu_export") + "   Ctrl+E",
                           command=self.app._export)
        m_file.add_separator()
        m_file.add_command(label=_("menu_clear_log") + "   Ctrl+L",
                           command=self.app._clr_log)

    def _build_tools_menu(self, menubar: Menu) -> None:
        m_tools = self._menu(menubar)
        menubar.add_cascade(label=_("menu_tools"), menu=m_tools)
        m_tools.add_command(label=_("wizard_title") + "…        Ctrl+P",
                            command=self.app._open_prompt_wizard)
        m_tools.add_separator()
        m_tools.add_command(label=_("phrase_title") + "…         Ctrl+B",
                            command=self.app._open_phrase_panel)
        m_tools.add_command(label=_("menu_switch_variants") + "   Ctrl+2",
                            command=self.app._switch_to_variant_tab)
        m_tools.add_command(label=_("menu_switch_queue") + "   Ctrl+Q",
                            command=self.app._switch_to_queue_tab)

    def _build_api_menu(self, menubar: Menu) -> None:
        m_api = self._menu(menubar)
        menubar.add_cascade(label=" 🔑  " + _("menu_api") + " ", menu=m_api)
        m_api.add_command(label="  " + _("menu_free_config"), command=self.app._open_wizard)
        m_api.add_command(label="  " + _("menu_paid_config"), command=self.app._open_paid_wizard)
        m_api.add_separator()

        # Free provider registration links
        m_free_links = self._menu(m_api)
        m_api.add_cascade(label="  " + _("menu_free_links"), menu=m_free_links)
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
        m_api.add_cascade(label="  " + _("menu_paid_links"), menu=m_paid_links)
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

        # 界面语言（zh-CN / en）——切换后重启生效
        m_lang = self._menu(m_set)
        m_set.add_cascade(label="  🌐  " + _("settings_language"), menu=m_lang)
        for code, native in self.app.SUPPORTED_LANGUAGES.items():
            m_lang.add_radiobutton(label=native, variable=self.app.lang_var,
                                   value=code, command=lambda c=code:
                                       self.app.settings_controller.set_language(c))

        m_set.add_separator()
        m_set.add_command(label="  🖼  " + _("settings_prefs_title") + "…",
                          command=self.app._open_app_settings)
        m_set.add_command(label="  ⌨  " + _("settings_shortcuts_title") + "…",
                          command=self.app._show_shortcuts)
        m_set.add_separator()
        m_set.add_command(label="  " + _("menu_check_update"),
                          command=self.app._check_update_menu)
        m_set.add_command(label="  " + _("menu_about"),
                          command=self.app._open_about)
