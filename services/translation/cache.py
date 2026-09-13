"""
services/translation/cache.py — Translation result cache
─────────────────────────────────────────────────────────
LRU cache for translation results to avoid redundant API calls
for the same source text.  Thread-safe.
"""
from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict


class TranslationCache:
    """Thread-safe LRU cache for translation results."""

    def __init__(self, max_size: int = 1000) -> None:
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _key(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        return hashlib.sha256(
            f"{source_lang}\0{target_lang}\0{text}".encode("utf-8")
        ).hexdigest()

    def get(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str | None:
        if not text or not text.strip():
            return None
        key = self._key(text, source_lang, target_lang)
        with self._lock:
            if key in self._cache:
                self._hits += 1
                self._cache.move_to_end(key)
                return self._cache[key]
            self._misses += 1
            return None

    def put(self, text: str, result: str, source_lang: str = "zh", target_lang: str = "en") -> None:
        if not text or not result:
            return
        key = self._key(text, source_lang, target_lang)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = result
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / max(1, self._hits + self._misses),
            }


# Global singleton
_translation_cache = TranslationCache()


def get_translation_cache() -> TranslationCache:
    """Get the global translation cache instance."""
    return _translation_cache
