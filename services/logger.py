"""
services/logger.py — 轻量日志服务
无任何 UI / 网络依赖。
"""
from datetime import datetime
import os
from typing import Callable, Optional
from config.settings import LOG_FILE


def log_to_file(msg: str) -> None:
    try:
        # Sanitize: prevent log injection via newlines
        safe = msg.replace('\n', '\\n').replace('\r', '\\r')
        # Rotate if > 5MB
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 5 * 1024 * 1024:
            backup = LOG_FILE + ".1"
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(LOG_FILE, backup)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {safe}\n")
    except Exception:
        pass


def make_log_callback(ui_cb: Optional[Callable[[str], None]] = None) -> Callable[[str], None]:
    def _cb(msg: str) -> None:
        log_to_file(msg)
        if ui_cb:
            ui_cb(msg)
    return _cb
