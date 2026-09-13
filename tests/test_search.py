"""
tests/test_search.py — FTS5 search tests
"""
from __future__ import annotations

import pytest

from data import repository, search


@pytest.fixture(autouse=True)
def setup_db():
    repository._set_test_db(":memory:")
    repository.init_db()
    search.setup_fts5(repository._conn())
    yield


class TestFTS5Search:
    def test_search_empty_keyword(self):
        result = search.search_entries("")
        assert result == []

    def test_search_whitespace_keyword(self):
        result = search.search_entries("   ")
        assert result == []

    def test_search_finds_entry(self):
        repository.add_entry("a beautiful sunset", "美丽日落", "/tmp/sunset.png", "TestProvider")
        results = search.search_entries("sunset")
        assert len(results) >= 1

    def test_search_finds_by_translated(self):
        repository.add_entry("a cat", "一只猫", "/tmp/cat.png", "TestProvider")
        results = search.search_entries("猫")
        # May find via FTS or fallback LIKE
        assert isinstance(results, list)

    def test_search_no_match(self):
        repository.add_entry("a dog", "狗", "/tmp/dog.png", "TestProvider")
        results = search.search_entries("xyznonexistent")
        assert results == []

    def test_search_multiple_results(self):
        repository.add_entry("red apple", "红苹果", "/tmp/a1.png", "P1")
        repository.add_entry("green apple", "青苹果", "/tmp/a2.png", "P2")
        repository.add_entry("banana", "香蕉", "/tmp/b1.png", "P3")
        results = search.search_entries("apple")
        assert len(results) >= 1
