"""
services/translation/__init__.py — Translation services
───────────────────────────────────────────────────────
Provides Chinese→English translation with rate limiting,
plus a result cache layer.

PERF-001 改造：
  - 缓存命中不访问网络、不受限流影响（cache 在锁外检查）
  - 限流等待改为分段可中断（token.cancel() 后 ≤0.1s 响应）
  - 隐私：文件日志不记录完整译文（仅长度），避免用户提示词
    全文落入 debug.log（§23.3）
"""
import hashlib
import re
import threading
import time
from typing import Callable, Optional
import requests

from services.generation.cancellation import CancellationToken
from services.generation.errors import GenerationCancelled

# Rate limiting for MyMemory free tier
_TRANS_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTERVAL = 1.5  # MyMemory free tier recommended interval
_WAIT_STEP = 0.1     # 限流等待的检查粒度（秒）


def has_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return bool(re.search(r'[一-鿿]', text))


def _log_privacy(log_cb, msg: str, translated: str = "") -> None:
    """UI 回调可见全文，文件日志只落哈希前缀 + 长度（§23.3）。"""
    if log_cb is None:
        return
    if translated:
        digest = hashlib.sha256(translated.encode("utf-8")).hexdigest()[:8]
        log_cb(f"翻译完成（len={len(translated)} hash={digest}）")
    else:
        log_cb(msg)


def _interruptible_wait(seconds: float, token: Optional[CancellationToken]) -> None:
    """分段等待限流间隔，期间响应取消。"""
    if token is None:
        time.sleep(seconds)
        return
    waited = 0.0
    while waited < seconds:
        token.throw_if_cancelled()
        time.sleep(min(_WAIT_STEP, seconds - waited))
        waited += _WAIT_STEP


def translate_zh_to_en(text: str, log_cb: Optional[Callable[[str], None]] = None,
                       token: Optional[CancellationToken] = None) -> str:
    """Translate Chinese text to English using MyMemory API.

    token: 可选取消令牌 —— 限流等待期间每 0.1s 检查一次，
    取消后抛出 GenerationCancelled（而非等满间隔）。
    """
    # Check cache first（锁外快速路径，不受限流影响）
    from services.translation.cache import get_translation_cache
    cache = get_translation_cache()
    cached = cache.get(text)
    if cached is not None:
        return cached

    MAX_PROMPT_CHARS = 2000
    if len(text) > MAX_PROMPT_CHARS:
        text = text[:MAX_PROMPT_CHARS]
        if log_cb:
            log_cb(f"提示词过长，已截断至 {MAX_PROMPT_CHARS} 字符")
    # 锁内只做限速等待与时间槽预占：15s 超时的 HTTP 请求若持锁，
    # 最慢请求会串行阻塞所有后续翻译调用
    with _TRANS_LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTERVAL:
            _interruptible_wait(_MIN_INTERVAL - gap, token)
        _LAST_DONE[0] = time.time()
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": "zh|en"}, timeout=15)
        translated = resp.json().get("responseData", {}).get("translatedText", "")
        if translated and "PLEASE SELECT" not in translated.upper() and len(translated) > 2:
            _log_privacy(log_cb, "翻译完成", translated)
            cache.put(text, translated)
            return translated
    except GenerationCancelled:
        raise
    except Exception as e:
        if log_cb:
            log_cb(f"翻译失败（使用原文）: {type(e).__name__}")
    return text


# Re-export cache
from services.translation.cache import TranslationCache, get_translation_cache

__all__ = [
    "has_chinese",
    "translate_zh_to_en",
    "TranslationCache",
    "get_translation_cache",
]
