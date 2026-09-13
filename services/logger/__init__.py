"""
services/logger/__init__.py — Logging services
─────────────────────────────────────────────
Provides both the original simple file logger and the new
async structured logger.
"""
from datetime import datetime
import os
from typing import Callable, Optional
from config.settings import LOG_FILE


def log_to_file(msg: str) -> None:
    """Simple file logger with rotation and sanitization."""
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
    """Create a logger that writes to file and optionally to UI."""
    def _cb(msg: str) -> None:
        log_to_file(msg)
        if ui_cb:
            ui_cb(msg)
    return _cb


# Re-export async logger components
from services.logger.async_logger import AsyncLogger, get_logger

__all__ = [
    "log_to_file",
    "make_log_callback",
    "AsyncLogger",
    "get_logger",
]
