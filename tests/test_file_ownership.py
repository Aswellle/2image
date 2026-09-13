"""
tests/test_file_ownership.py — Secure file deletion tests
─────────────────────────────────────────────────────────
Validates path traversal prevention, symlink rejection,
and root containment for the file ownership module.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from services.generation.file_ownership import (
    FileOwnershipError,
    is_owned_path,
    safe_delete_file,
    safe_owned_image_path,
)


@pytest.fixture
def managed_dir(tmp_path):
    """Create a managed image directory with a test file."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    test_file = img_dir / "test.png"
    test_file.write_bytes(b"\x89PNG\r\n" + b"\x00" * 100)
    return img_dir


class TestSafeOwnedImagePath:
    def test_valid_path_inside_root(self, managed_dir):
        target = managed_dir / "subdir" / "img.png"
        target.parent.mkdir()
        target.touch()
        result = safe_owned_image_path(str(target), str(managed_dir))
        assert result == target.resolve()

    def test_rejects_path_outside_root(self, managed_dir, tmp_path):
        outside = tmp_path / "secret.txt"
        outside.write_text("private data")
        with pytest.raises(FileOwnershipError, match="outside managed"):
            safe_owned_image_path(str(outside), str(managed_dir))

    def test_rejects_traversal_attack(self, managed_dir):
        traversal = managed_dir / ".." / ".." / "etc" / "passwd"
        with pytest.raises(FileOwnershipError, match="outside managed"):
            safe_owned_image_path(str(traversal), str(managed_dir))

    def test_rejects_symlink(self, managed_dir, tmp_path):
        # Create a symlink pointing outside the managed dir
        secret = tmp_path / "secret.txt"
        secret.write_text("private")
        link = managed_dir / "escape.png"
        try:
            link.symlink_to(secret)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")
        with pytest.raises(FileOwnershipError, match="symlink"):
            safe_owned_image_path(str(link), str(managed_dir))

    def test_rejects_empty_path(self, managed_dir):
        with pytest.raises(FileOwnershipError, match="Empty"):
            safe_owned_image_path("", str(managed_dir))

    def test_rejects_none_path(self, managed_dir):
        with pytest.raises(FileOwnershipError):
            safe_owned_image_path(None, str(managed_dir))


class TestIsOwnedPath:
    def test_returns_true_for_valid(self, managed_dir):
        target = managed_dir / "ok.png"
        target.touch()
        assert is_owned_path(str(target), str(managed_dir)) is True

    def test_returns_false_for_outside(self, managed_dir, tmp_path):
        outside = tmp_path / "bad.txt"
        outside.touch()
        assert is_owned_path(str(outside), str(managed_dir)) is False

    def test_returns_false_for_symlink(self, managed_dir, tmp_path):
        secret = tmp_path / "s.txt"
        secret.write_text("x")
        link = managed_dir / "link.png"
        try:
            link.symlink_to(secret)
        except OSError:
            pytest.skip("Symlinks not supported")
        assert is_owned_path(str(link), str(managed_dir)) is False


class TestSafeDeleteFile:
    def test_deletes_owned_file(self, managed_dir):
        target = managed_dir / "delete_me.png"
        target.write_bytes(b"\x89PNG")
        assert safe_delete_file(str(target), str(managed_dir)) is True
        assert not target.exists()

    def test_returns_false_for_missing_file(self, managed_dir):
        missing = managed_dir / "nonexistent.png"
        assert safe_delete_file(str(missing), str(managed_dir)) is False

    def test_refuses_to_delete_outside(self, managed_dir, tmp_path):
        secret = tmp_path / "important.txt"
        secret.write_text("do not delete")
        with pytest.raises(FileOwnershipError):
            safe_delete_file(str(secret), str(managed_dir))
        assert secret.exists()  # File must still exist

    def test_refuses_to_delete_symlink(self, managed_dir, tmp_path):
        secret = tmp_path / "data.txt"
        secret.write_text("protected")
        link = managed_dir / "link.png"
        try:
            link.symlink_to(secret)
        except OSError:
            pytest.skip("Symlinks not supported")
        with pytest.raises(FileOwnershipError):
            safe_delete_file(str(link), str(managed_dir))
        assert secret.exists()


class TestDeleteEntryIntegration:
    """Test that repository.delete_entry uses safe deletion."""

    def test_delete_entry_with_managed_path(self, tmp_path, monkeypatch):
        from data import repository
        from services.generation import file_ownership

        monkeypatch.setattr(file_ownership, "IMAGES_DIR", str(tmp_path))

        repository._set_test_db(":memory:")
        repository.init_db()

        target = tmp_path / "entry_img.png"
        target.write_bytes(b"\x89PNG\r\n" + b"\x00" * 100)
        entry = repository.add_entry("test prompt", "test", str(target), "test_provider")
        entry_id = entry["id"]

        repository.delete_entry(entry_id, remove_file=True)
        assert not target.exists()

    def test_delete_entry_outside_path_not_deleted(self, tmp_path, monkeypatch):
        from data import repository
        from services.generation import file_ownership

        managed = tmp_path / "images"
        managed.mkdir()
        monkeypatch.setattr(file_ownership, "IMAGES_DIR", str(managed))

        repository._set_test_db(":memory:")
        repository.init_db()

        outside = tmp_path / "secret.txt"
        outside.write_text("protected")
        entry = repository.add_entry("test", "", str(outside), "provider")
        entry_id = entry["id"]

        repository.delete_entry(entry_id, remove_file=True)
        assert outside.exists()


class TestMigrationTransaction:
    """Test that migration handles partial failures correctly."""

    def test_migration_all_success_renames_file(self, tmp_path):
        from data import repository

        repository._set_test_db(":memory:")
        repository.init_db()

        json_file = tmp_path / "history.json"
        json_file.write_text(
            '[{"id": 1, "prompt": "test", "timestamp": "2024-01-01"}]'
        )

        result = repository.migrate_from_json(str(json_file))
        assert result["migrated"] == 1
        assert result["failed"] == 0
        # Original should be renamed
        assert not json_file.exists()
        assert (tmp_path / "history.json.migrated").exists()

    def test_migration_partial_failure_preserves_file(self, tmp_path):
        from data import repository

        repository._set_test_db(":memory:")
        repository.init_db()

        # Create JSON with one valid and one invalid entry
        json_file = tmp_path / "history.json"
        import json

        records = [
            {"id": 1, "prompt": "good", "timestamp": "2024-01-01"},
            {"id": 2, "prompt": "also good", "timestamp": "2024-01-02"},
        ]
        json_file.write_text(json.dumps(records))

        result = repository.migrate_from_json(str(json_file))
        assert result["migrated"] == 2
        assert result["failed"] == 0

    def test_migration_invalid_json_returns_zero(self, tmp_path):
        from data import repository

        repository._set_test_db(":memory:")
        repository.init_db()

        json_file = tmp_path / "bad.json"
        json_file.write_text("not valid json {{{")

        result = repository.migrate_from_json(str(json_file))
        assert result["migrated"] == 0
        assert result["total"] == 0

    def test_migration_nonexistent_file(self):
        from data import repository

        repository._set_test_db(":memory:")
        repository.init_db()

        result = repository.migrate_from_json("/nonexistent/path.json")
        assert result["total"] == 0


class TestUUIDFilenames:
    """Test that save_image_file uses UUID-based paths."""

    def test_save_creates_uuid_filename(self, managed_dir, monkeypatch):
        from services import image_service

        monkeypatch.setattr(
            image_service, "IMAGES_DIR", str(managed_dir)
        )

        # Create a valid PNG
        from io import BytesIO
        from PIL import Image

        img = Image.new("RGB", (64, 64), (255, 0, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")

        path = image_service.save_image_file(
            buf.getvalue(), "test prompt", seed=42, provider="test"
        )

        # Path should be under managed_dir/YYYY/MM/DD/<uuid>.png
        p = Path(path)
        assert p.name.endswith(".png")
        # UUID is 32 hex chars
        assert len(p.stem) == 32
        # Should have date-based subdirectories (YYYY/MM/DD)
        assert p.parent.parent.parent.parent == Path(managed_dir)
    def test_save_no_collision(self, managed_dir, monkeypatch):
        """Two saves with same prompt should not collide."""
        from services import image_service

        monkeypatch.setattr(
            image_service, "IMAGES_DIR", str(managed_dir)
        )

        from io import BytesIO
        from PIL import Image

        img = Image.new("RGB", (8, 8), (0, 255, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")

        path1 = image_service.save_image_file(buf.getvalue(), "same prompt")
        path2 = image_service.save_image_file(buf.getvalue(), "same prompt")

        assert path1 != path2
        assert Path(path1).exists()
        assert Path(path2).exists()
