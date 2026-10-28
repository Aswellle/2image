"""
data/file_ownership.py — Secure file deletion
───────────────────────────────────────────────
Prevents path traversal and symlink attacks when deleting
generated images.  All file operations MUST go through
``safe_owned_image_path()`` before touching the filesystem.

Deletion goes to the Windows Recycle Bin (SHFileOperationW with
FOF_ALLOWUNDO) so a misclick stays recoverable; permanent unlink
is only the fallback for platforms/drives without a recycle bin.
"""

from __future__ import annotations

import sys
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
        raise FileOwnershipError(f"Refusing to operate on symlink: {image_path}")

    # Containment check: target must be root or under root
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise FileOwnershipError(f"Image path '{image_path}' is outside managed directory '{root}'") from exc

    return target


def is_owned_path(image_path: str | None, root_dir: str | None = None) -> bool:
    """Return True if path is safely inside root_dir (non-raising)."""
    try:
        safe_owned_image_path(image_path, root_dir)
        return True
    except FileOwnershipError:
        return False


def _send_to_recycle_bin(path: Path) -> bool:
    """Move ``path`` to the Windows Recycle Bin. Non-Windows or any shell
    failure returns False so the caller can fall back to unlink()."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", ctypes.c_uint),
                ("pFrom", ctypes.c_wchar_p),
                ("pTo", ctypes.c_wchar_p),
                ("fFlags", ctypes.c_ushort),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", ctypes.c_wchar_p),
            ]

        FO_DELETE = 3
        FOF_SILENT = 0x0004
        FOF_NOCONFIRMATION = 0x0010
        FOF_ALLOWUNDO = 0x0040
        FOF_NOERRORUI = 0x0400

        op = SHFILEOPSTRUCTW()
        op.hwnd = None
        op.wFunc = FO_DELETE
        # pFrom 必须双 NUL 结尾；c_wchar_p 自带一个，再补一个
        op.pFrom = str(path) + "\x00"
        op.pTo = None
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        return rc == 0 and not op.fAnyOperationsAborted
    except Exception:
        return False


def safe_delete_file(image_path: str | None, root_dir: str | None = None) -> bool:
    """
    Safely delete a file that must be inside the managed directory.
    Returns True if file was deleted, False if it didn't exist.

    Prefers the Recycle Bin; falls back to permanent unlink when the
    shell operation is unavailable (non-Windows, network drives...).
    """
    path = safe_owned_image_path(image_path, root_dir)
    if path.exists() and not path.is_symlink():
        if not _send_to_recycle_bin(path):
            path.unlink()
        return True
    return False
