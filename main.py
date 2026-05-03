#!/usr/bin/env python3
"""
main.py — 程序入口
──────────────────
职责：DPI 感知初始化 → 检查首次启动 → 弹出引导 → 数据库初始化 → 启动主窗口。
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# DPI 感知（Windows）
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

if __name__ == "__main__":
    from config.settings import APP_DIR, CONFIG_FILE
    os.makedirs(APP_DIR, exist_ok=True)

    # 首次启动弹出引导
    if not os.path.exists(CONFIG_FILE):
        try:
            from ui.wizard_free import launch_wizard
            launch_wizard()
        except Exception as e:
            print(f"[wizard] 引导窗口启动失败（不影响主程序）：{e}")

    from ui.app import App
    app = App()
    app.mainloop()
