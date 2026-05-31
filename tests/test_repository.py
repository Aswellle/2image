"""Tests for data/repository.py CRUD operations."""
import pytest
from data import repository


@pytest.fixture(autouse=True)
def setup_db():
    repository._set_test_db(":memory:")
    repository.init_db()
    yield


def test_add_and_get_entry():
    entry = repository.add_entry("test prompt", "translated", "/tmp/test.png", "TestProvider")
    assert entry["prompt"] == "test prompt"
    assert entry["provider"] == "TestProvider"
    assert "id" in entry


def test_get_all_entries_empty():
    entries = repository.get_all_entries()
    assert len(entries) == 0


def test_get_all_entries_with_data():
    repository.add_entry("prompt 1", "", "/tmp/1.png", "P1")
    repository.add_entry("prompt 2", "", "/tmp/2.png", "P2")
    entries = repository.get_all_entries()
    assert len(entries) == 2


def test_tag_operations():
    repository.add_entry("test", "", "/tmp/t.png", "T")
    repository.update_tags(1, "tag1, tag2, tag3")
    tags = repository.get_all_tags()
    assert "tag1" in tags
    assert "tag2" in tags
    assert "tag3" in tags


def test_tag_filter():
    repository.add_entry("p1", "", "/tmp/a.png", "X")
    repository.add_entry("p2", "", "/tmp/b.png", "X")
    repository.update_tags(1, "\u98ce\u666f")
    repository.update_tags(2, "\u4eba\u50cf")
    filtered = repository.get_all_entries(tag_filter="\u98ce\u666f")
    assert len(filtered) == 1
    assert filtered[0]["prompt"] == "p1"


def test_stats():
    repository.add_entry("p1", "", "/tmp/a.png", "X")
    repository.add_entry("p2", "", "/tmp/b.png", "Y")
    stats = repository.get_stats()
    assert stats["total"] == 2
    assert "providers" in stats


def test_favorite_toggle():
    repository.add_entry("test", "", "/tmp/t.png", "T")
    repository.toggle_favorite(1, True)
    entry = repository.get_entry(1)
    assert entry["favorited"] == 1
    repository.toggle_favorite(1, False)
    entry = repository.get_entry(1)
    assert entry["favorited"] == 0


def test_delete_entry():
    repository.add_entry("test", "", "/tmp/t.png", "T")
    assert repository.count_entries() == 1
    repository.delete_entry(1, remove_file=False)
    assert repository.count_entries() == 0
