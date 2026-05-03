"""
services/logger.py — 调试日志
"""
import os
from config.settings import LOG_FILE


def log_to_file(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def get_log_content() -> str:
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return ""


def clear_log() -> None:
    try:
        open(LOG_FILE, "w").close()
    except Exception:
        pass


from datetime import datetime
