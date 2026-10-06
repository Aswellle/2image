"""
services/updater/errors.py — stable update error codes & exceptions
───────────────────────────────────────────────────────────────────
Every failure in the update pipeline carries a machine-readable code
(UPDATE_*).  UI layers map the code to localized text via the
``upd_err_*`` i18n keys and log the technical ``detail`` separately,
so users always see an explainable state instead of a raw traceback.
"""
from __future__ import annotations

from enum import Enum


class UpdateErrorCode(Enum):
    OK = "UPDATE_OK"
    NO_UPDATE = "UPDATE_NO_UPDATE"
    NETWORK_ERROR = "UPDATE_NETWORK_ERROR"
    HTTP_ERROR = "UPDATE_HTTP_ERROR"
    MANIFEST_INVALID = "UPDATE_MANIFEST_INVALID"
    VERSION_INVALID = "UPDATE_VERSION_INVALID"
    DOWNLOAD_FAILED = "UPDATE_DOWNLOAD_FAILED"
    SIZE_MISMATCH = "UPDATE_SIZE_MISMATCH"
    HASH_MISMATCH = "UPDATE_HASH_MISMATCH"
    INSTALLER_LAUNCH_FAILED = "UPDATE_INSTALLER_LAUNCH_FAILED"
    INSTALL_FAILED = "UPDATE_INSTALL_FAILED"
    POST_VERIFY_FAILED = "UPDATE_POST_VERIFY_FAILED"
    ROLLBACK_FAILED = "UPDATE_ROLLBACK_FAILED"
    CANCELLED = "UPDATE_CANCELLED"


class UpdateError(RuntimeError):
    """Update pipeline failure with a stable machine-readable code."""

    def __init__(self, code: UpdateErrorCode, detail: str = ""):
        self.code = code
        self.detail = detail or code.value
        super().__init__(self.detail)


class ChecksumMismatchError(UpdateError):
    """Downloaded installer SHA-256 differs from the manifest.

    Installing in this state is forbidden — the file must be deleted
    and the flow must stop before any installer is launched.
    """

    def __init__(self, detail: str = ""):
        super().__init__(UpdateErrorCode.HASH_MISMATCH, detail)
