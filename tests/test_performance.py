"""
tests/test_performance.py — Performance optimization tests
─────────────────────────────────────────────────────────────
Tests for translation cache, async logger, and keyset pagination.
"""
from __future__ import annotations

import pytest

from services.translation.cache import TranslationCache, get_translation_cache
from services.logger import AsyncLogger, get_logger
from data import repository




@pytest.fixture(autouse=True)
def setup_db():
    repository._set_test_db(":memory:")
    repository.init_db()
    yield


class TestTranslationCache:
    def test_cache_miss_returns_none(self):
        cache = TranslationCache()
        assert cache.get("hello") is None

    def test_cache_hit_after_put(self):
        cache = TranslationCache()
        cache.put("hello", "world")
        assert cache.get("hello") == "world"

    def test_cache_different_languages(self):
        cache = TranslationCache()
        cache.put("hello", "world", source_lang="en", target_lang="fr")
        assert cache.get("hello", source_lang="en", target_lang="fr") == "world"
        assert cache.get("hello", source_lang="en", target_lang="es") is None

    def test_cache_empty_text_returns_none(self):
        cache = TranslationCache()
        assert cache.get("") is None
        assert cache.get("   ") is None

    def test_cache_lru_eviction(self):
        cache = TranslationCache(max_size=3)
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")
        cache.put("d", "4")  # Should evict "a"
        assert cache.get("a") is None
        assert cache.get("d") == "4"

    def test_cache_stats(self):
        cache = TranslationCache()
        cache.put("a", "1")
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_cache_clear(self):
        cache = TranslationCache()
        cache.put("a", "1")
        cache.clear()
        assert cache.get("a") is None
        assert cache.stats["size"] == 0

    def test_singleton_instance(self):
        cache = get_translation_cache()
        assert isinstance(cache, TranslationCache)


class TestAsyncLogger:
    def test_singleton_setup(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        AsyncLogger.setup(log_file=log_file)
        # Second call should be no-op
        AsyncLogger.setup(log_file=log_file)
        AsyncLogger.shutdown()

    def test_logger_returns_logger_instance(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        AsyncLogger.setup(log_file=log_file)
        logger = get_logger("test_module")
        assert logger is not None
        AsyncLogger.shutdown()


class TestKeysetPagination:
    def test_returns_entries_in_order(self):
        for i in range(10):
            repository.add_entry(f"prompt {i}", "", f"/tmp/{i}.png", "P")
        entries = repository.get_entries_keyset(limit=5)
        assert len(entries) == 5
        # Should be in descending ID order
        ids = [e["id"] for e in entries]
        assert ids == sorted(ids, reverse=True)

    def test_keyset_after_id(self):
        for i in range(10):
            repository.add_entry(f"prompt {i}", "", f"/tmp/{i}.png", "P")
        # Get first 5
        first = repository.get_entries_keyset(limit=5)
        last_id = first[-1]["id"]
        # Get next 5 after last_id
        next_entries = repository.get_entries_keyset(after_id=last_id, limit=5)
        assert len(next_entries) == 5
        # All should have id < last_id
        for e in next_entries:
            assert e["id"] < last_id

    def test_keyset_no_duplicates(self):
        for i in range(20):
            repository.add_entry(f"prompt {i}", "", f"/tmp/{i}.png", "P")
        all_entries = []
        after_id = 0
        for _ in range(4):
            batch = repository.get_entries_keyset(after_id=after_id, limit=5)
            if not batch:
                break
            all_entries.extend(batch)
            after_id = batch[-1]["id"]
        # No duplicates
        ids = [e["id"] for e in all_entries]
        assert len(ids) == len(set(ids))

    def test_keyset_limit_zero_returns_all(self):
        for i in range(5):
            repository.add_entry(f"prompt {i}", "", f"/tmp/{i}.png", "P")
        entries = repository.get_entries_keyset(limit=0)
        assert len(entries) == 5
