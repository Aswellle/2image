"""
services/translation/__init__.py — Translation services
───────────────────────────────────────────────────────
Provides Chinese→English translation with rate limiting,
plus a result cache layer.
"""
import re
import threading
import time
from typing import Callable, Optional
import requests

# Rate limiting for MyMemory free tier
_TRANS_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTERVAL = 1.5  # MyMemory free tier recommended interval


def has_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return bool(re.search(r'[一-鿿]', text))


def translate_zh_to_en(text: str, log_cb: Optional[Callable[[str], None]] = None) -> str:
    """Translate Chinese text to English using MyMemory API."""
    # Check cache first
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
    with _TRANS_LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - gap)
        try:
            resp = requests.get(
                "https://api.mymemory.translated.net/get",
                params={"q": text, "langpair": "zh|en"}, timeout=15)
            translated = resp.json().get("responseData", {}).get("translatedText", "")
            if translated and "PLEASE SELECT" not in translated.upper() and len(translated) > 2:
                if log_cb:
                    log_cb(f"翻译成功: {translated}")
                cache.put(text, translated)
                return translated
        except Exception as e:
            if log_cb:
                log_cb(f"翻译失败（使用原文）: {e}")
        finally:
            _LAST_DONE[0] = time.time()
    return text


# Re-export cache
from services.translation.cache import TranslationCache, get_translation_cache

__all__ = [
    "has_chinese",
    "translate_zh_to_en",
    "TranslationCache",
    "get_translation_cache",
]
