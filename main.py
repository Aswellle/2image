#!/usr/bin/env python3
"""
main.py — 程序入口
───────────────────
职责：DPI 感知初始化 → 数据库初始化 → 启动 Tkinter 主窗口。
不包含任何业务逻辑，保持入口文件极简。
"""
import tkinter as tk
import sys
import os

_APP_USER_MODEL_ID = "Aswellle.2image"
_ICON_FILE = "ICON_256x256.ico"

# 将项目根目录加入 Python 路径，确保包导入正常
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _resource_path(filename: str) -> str:
    return os.path.join(
        getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))),
        filename,
    )


def _set_windows_app_user_model_id():
    if sys.platform == "win32":
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(_APP_USER_MODEL_ID)


def _configure_window_icon(root: tk.Tk):
    root.iconbitmap(_resource_path(_ICON_FILE))


def _enable_dpi_awareness():
    """Windows 下启用 DPI 感知，避免界面模糊。"""
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def main():
    _set_windows_app_user_model_id()
    _enable_dpi_awareness()

    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard (~40 Mpx)

    # ── 字体初始化（加载缓存字体，后台下载缺失字体）────────────
    from config.fonts import init_fonts
    init_fonts()

    # ── 数据库初始化（建表 / 迁移旧 JSON）──────────────────────
    from data.repository import init_db, migrate_from_json
    from config.settings import APP_DIR
    init_db()
    old_json = os.path.join(APP_DIR, "history.json")
    migrated = migrate_from_json(old_json)
    if migrated:
        print(f"[迁移] 已从 history.json 导入 {migrated} 条记录到 SQLite")

    # ── 启动 UI ─────────────────────────────────────────────────
    from ui.app import App
    root = tk.Tk()
    _configure_window_icon(root)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
