"""
services/generation/file_ownership.py — Secure file deletion
───────────────────────────────────────────────────────────
Prevents path traversal and symlink attacks when deleting
generated images.  All file operations MUST go through
``safe_owned_image_path()`` before touching the filesystem.
"""
from __future__ import annotations

from pathlib import Path

from config.settings import IMAGES_DIR


class FileOwnershipError(ValueError):
    """Raised when a path is outside the managed image directory."""


def safe_owned_image_path(image_path: str | None, root_dir: str | None = None) -> Path:
    """
    Validate that ``image_path`` is strictly inside ``root_dir``.

    Returns the resolved Path on success.
    Raises FileOwnershipError on traversal/symlink escape.
    """
    root = Path(root_dir or IMAGES_DIR).resolve()

    if not image_path:
        raise FileOwnershipError("Empty image path")

    target = Path(image_path).resolve(strict=False)

    # Reject symlinks — they could point outside the root
    if target.is_symlink():
        raise FileOwnershipError(
            f"Refusing to operate on symlink: {image_path}"
        )

    # Containment check: target must be root or under root
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise FileOwnershipError(
            f"Image path '{image_path}' is outside managed directory '{root}'"
        ) from exc

    return target


def is_owned_path(image_path: str | None, root_dir: str | None = None) -> bool:
    """Return True if path is safely inside root_dir (non-raising)."""
    try:
        safe_owned_image_path(image_path, root_dir)
        return True
    except FileOwnershipError:
        return False


def safe_delete_file(image_path: str | None, root_dir: str | None = None) -> bool:
    """
    Safely delete a file that must be inside the managed directory.
    Returns True if file was deleted, False if it didn't exist.
    """
    path = safe_owned_image_path(image_path, root_dir)
    if path.exists() and not path.is_symlink():
        path.unlink()
        return True
    return False
