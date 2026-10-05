"""
services/logger/__init__.py — Logging services
─────────────────────────────────────────────
log_to_file() 是应用主日志通道。PERF-002 改造：
调用线程只做 sanitize + 入队（put_nowait，队满丢弃），磁盘 I/O
（open/write/rotate）全部由单一后台 writer 线程完成 —— 高频生成时
worker 线程不再被同步文件写阻塞。

AsyncLogger 是 stdlib logging 通道的 QueueHandler 实现（结构化 JSON），
供需要 correlation 字段的模块选用。
"""
import os
import queue
import threading
from datetime import datetime
from typing import Callable, Optional

from config.settings import LOG_FILE

# ── 异步写线程（PERF-002）──────────────────────────────────────
_QUEUE: "queue.Queue[Optional[str]]" = queue.Queue(maxsize=10000)
_WRITER_LOCK = threading.Lock()
_writer_started = False


def _rotate_if_needed() -> None:
    if LOG_FILE and LOG_FILE.endswith(".log"):
        try:
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 5 * 1024 * 1024:
                backup = LOG_FILE + ".1"
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(LOG_FILE, backup)
        except Exception:
            pass


def _write_sync(msg: str) -> None:
    """实际磁盘写入（仅 writer 线程调用）。"""
    try:
        _rotate_if_needed()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _writer_loop() -> None:
    while True:
        msg = _QUEUE.get()
        try:
            if msg is None:          # shutdown sentinel
                break
            _write_sync(msg)
        finally:
            _QUEUE.task_done()  # 未调用 join() 将永久挂起


def _ensure_writer() -> None:
    global _writer_started
    if _writer_started:
        return
    with _WRITER_LOCK:
        if _writer_started:
            return
        t = threading.Thread(target=_writer_loop, name="log-writer", daemon=True)
        t.start()
        _writer_started = True


def log_to_file(msg: str) -> None:
    """异步文件日志：调用线程不入磁盘，绝不阻塞生成/UI 线程。"""
    try:
        safe = msg.replace('\n', '\\n').replace('\r', '\\r')
        _ensure_writer()
        try:
            _QUEUE.put_nowait(safe)
        except queue.Full:
            pass  # 背压时丢弃日志，绝不阻塞业务线程
    except Exception:
        pass


def flush_logs(timeout: float = 2.0) -> None:
    """等待队列中已排队的日志落盘（用于测试/优雅退出）。

    带 timeout 上限轮询 unfinished_tasks，超时即返回（writer
    死亡等异常情况下不再无限等待）。
    """
    import time as _time
    try:
        _ensure_writer()
        deadline = _time.monotonic() + max(0.0, float(timeout))
        while _QUEUE.unfinished_tasks > 0 and _time.monotonic() < deadline:
            _time.sleep(0.02)
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
    "flush_logs",
    "make_log_callback",
    "AsyncLogger",
    "get_logger",
]
