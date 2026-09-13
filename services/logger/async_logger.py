"""
services/logger/async_logger.py — Async structured logger
─────────────────────────────────────────────────────────
Replaces synchronous file-per-log-call with QueueHandler +
RotatingFileHandler pattern.  Worker thread handles all disk I/O.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import queue
import threading

from config.settings import LOG_FILE


class StructuredFormatter(logging.Formatter):
    """JSON structured log format with correlation fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        # Add optional correlation fields
        for field in ("job_id", "provider_id", "request_id", "phase", "latency_ms", "error_code"):
            val = getattr(record, field, None)
            if val is not None:
                log_entry[field] = val
        return json.dumps(log_entry, ensure_ascii=False)


class AsyncLogger:
    """Async logger with queue-based worker thread."""

    _initialized = False
    _lock = threading.Lock()
    _listener = None

    @classmethod
    def setup(
        cls,
        log_file: str = LOG_FILE,
        max_bytes: int = 5 * 1024 * 1024,  # 5 MB
        backup_count: int = 3,
        level: int = logging.INFO,
    ) -> None:
        """Initialize the async logger (idempotent)."""
        with cls._lock:
            if cls._initialized:
                return

            # Create log directory if needed
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            # Queue for log records
            log_queue: queue.Queue[logging.LogRecord] = queue.Queue(maxsize=10000)

            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )
            file_handler.setFormatter(StructuredFormatter())

            # Queue listener (worker thread)
            listener = logging.handlers.QueueListener(log_queue, file_handler)
            listener.start()

            # Queue handler for producers
            queue_handler = logging.handlers.QueueHandler(log_queue)
            queue_handler.setLevel(level)

            # Configure root logger
            root = logging.getLogger()
            root.addHandler(queue_handler)
            root.setLevel(level)

            cls._initialized = True
            cls._listener = listener

    @classmethod
    def shutdown(cls) -> None:
        """Graceful shutdown."""
        with cls._lock:
            if cls._initialized and cls._listener:
                cls._listener.stop()
                cls._initialized = False


def get_logger(name: str = "text2image") -> logging.Logger:
    """Get a configured logger."""
    if not AsyncLogger._initialized:
        AsyncLogger.setup()
    return logging.getLogger(name)
