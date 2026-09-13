"""
services/application/settings_controller.py — Settings window controller
─────────────────────────────────────────────────────────────────────────
Extracts settings/preferences windows from App to slim down
the main window class.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from config.settings import save_config
from config.fonts import F
from config.theme import DARK_THEME as C
from config.i18n import _


class SettingsController:
    """Manages application settings windows."""

    def __init__(self, app) -> None:
        self.app = app
        self.root = app.root

    def show_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog."""
        win = tk.Toplevel(self.root)
        win.title("⌨ 快捷键说明")
        win.configure(bg=C["bg"])
        win.resizable(False, False)
        win.grab_set()
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 520) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 460) // 2
        win.geometry(f"520x460+{max(0, x)}+{max(0, y)}")

        hdr = tk.Frame(win, bg=C["acc"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="⌨  快捷键说明", font=F["h1"],
                 bg=C["acc"], fg="white").pack(side="left", padx=16, pady=10)

        body = tk.Frame(win, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=20, pady=16)

        rows = [
            ("生成 / 重新生成", "Ctrl + Enter  /  Ctrl + R"),
            ("AI 提示词助手", "Ctrl + P"),
            ("📚 提示词片段库", "Ctrl + B"),
            ("另存为", "Ctrl + S"),
            ("导出历史记录", "Ctrl + E"),
            ("打开独立查看器", "Ctrl + O"),
            ("清空调试日志", "Ctrl + L"),
        ]
        for i, (action, keys) in enumerate(rows):
            rb = C["panel"] if i % 2 == 0 else C["bg"]
            row = tk.Frame(body, bg=rb)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=action, font=F["input"], bg=rb, fg=C["text"],
                     width=20, anchor="w").pack(side="left", padx=(10, 0), pady=6)
            tk.Label(row, text=keys, font=F["mono_lg"],
                     bg=rb, fg=C["ok"], anchor="w").pack(side="left", padx=12, pady=6)

        tk.Button(win, text=_("btn_close"), font=F["input"], bg=C["acc"], fg="white",
                  bd=0, padx=24, pady=6, cursor="hand2", command=win.destroy
                  ).pack(pady=(8, 16))

    def show_app_settings(self) -> None:
        """Show application preferences dialog."""
        win = tk.Toplevel(self.root)
        win.title("🖼 应用偏好设置")
        win.configure(bg=C["bg"])
        win.resizable(False, False)
        win.grab_set()
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 460) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 360) // 2
        win.geometry(f"460x360+{max(0, x)}+{max(0, y)}")

        hdr = tk.Frame(win, bg=C["acc"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="🖼  应用偏好设置", font=F["h1"],
                 bg=C["acc"], fg="white").pack(side="left", padx=16, pady=10)

        body = tk.Frame(win, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=16)

        tk.Label(body, text="默认生成尺寸", font=F["btn"],
                 bg=C["bg"], fg=C["sub"]).pack(anchor="w", pady=(0, 4))
        sz_var = tk.StringVar(value=self.app.cfg.get("default_size", "1024x1024").replace("×", "x"))
        ttk.Combobox(body, textvariable=sz_var, state="readonly", width=20,
                     values=["512x512", "768x768", "1024x1024", "1024x576", "1280x720",
                             "1920x1080", "576x1024", "720x1280", "768x1024"]
                     ).pack(anchor="w", pady=(0, 14))

        tk.Label(body, text="启动行为", font=F["btn"],
                 bg=C["bg"], fg=C["sub"]).pack(anchor="w", pady=(0, 4))
        wiz_var = tk.BooleanVar(value=self.app.cfg.get("show_wizard_on_start", True))
        tk.Checkbutton(body, text="启动时显示免费接口配置向导",
                       variable=wiz_var, font=F["body"], bg=C["bg"], fg=C["text"],
                       activebackground=C["bg"], selectcolor=C["entry"]).pack(anchor="w")

        st = tk.Label(body, text="", font=F["body"], bg=C["bg"], fg=C["ok"])
        st.pack(anchor="w", pady=(12, 0))

        def _save() -> None:
            self.app.cfg["default_size"] = sz_var.get()
            self.app.cfg["show_wizard_on_start"] = wiz_var.get()
            save_config(self.app.cfg)
            self.app.content.szv.set(sz_var.get())
            st.config(text="✅ 已保存！")
            win.after(1200, win.destroy)

        bot = tk.Frame(win, bg=C["panel"])
        bot.pack(fill="x", side="bottom")
        tk.Button(bot, text=_("btn_save"), font=F["btn"], bg=C["ok"], fg="#0a1a0a",
                  bd=0, padx=24, pady=8, cursor="hand2", command=_save
                  ).pack(side="right", padx=16, pady=10)
        tk.Button(bot, text=_("btn_cancel"), font=F["body"], bg=C["panel"], fg=C["sub"],
                  bd=0, padx=16, pady=8, cursor="hand2", command=win.destroy
                  ).pack(side="right", pady=10)
