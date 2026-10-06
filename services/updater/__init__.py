"""
services/updater — in-app self-update protocol package
──────────────────────────────────────────────────────
Layered modules (check → download → verify → install → confirm):

    version.py    current version source + SemVer parsing/comparison
    manifest.py   update.json manifest fetch + strict validation
    downloader.py streaming download (.partial) + size/SHA-256 gate
    installer.py  Inno Setup silent install command construction
    state.py      update state machine, pending/confirm markers,
                  auto-check cache, update log, backup/rollback
    errors.py     stable error codes mapped to UI text

Design rules (see docs update plan):
  · update.json on GitHub Releases is the ONLY production channel —
    no Releases API, no HTML scraping, no rate limits
  · a manifest that fails any validation rule must never trigger a
    download, let alone an install
  · the running app never modifies its own exe; the independent
    updater (tools/updater) takes over after the app exits
  · all network/disk work is blocking — callers must run it on a
    worker thread and marshal UI updates back via root.after
"""
from services.updater.errors import (
    ChecksumMismatchError,
    UpdateError,
    UpdateErrorCode,
)
from services.updater.version import (
    SemVer,
    VersionError,
    get_current_version,
    is_newer,
    is_packaged,
    parse_version,
)
from services.updater.manifest import (
    MANIFEST_URL,
    RELEASES_PAGE,
    UpdateAsset,
    UpdateManifest,
    evaluate_manifest,
    fetch_manifest,
    validate_manifest,
)
from services.updater.state import (
    UpdateFlow,
    UpdateState,
    append_update_log,
    confirm_pending_update,
    dismiss,
    is_dismissed,
    mark_checked,
    should_auto_check,
)

__all__ = [
    "ChecksumMismatchError",
    "UpdateError",
    "UpdateErrorCode",
    "SemVer",
    "VersionError",
    "get_current_version",
    "is_newer",
    "is_packaged",
    "parse_version",
    "MANIFEST_URL",
    "RELEASES_PAGE",
    "UpdateAsset",
    "UpdateManifest",
    "evaluate_manifest",
    "fetch_manifest",
    "validate_manifest",
    "UpdateFlow",
    "UpdateState",
    "append_update_log",
    "confirm_pending_update",
    "dismiss",
    "is_dismissed",
    "mark_checked",
    "should_auto_check",
]
