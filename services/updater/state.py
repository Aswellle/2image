"""
services/updater/state.py — update state machine + on-disk markers
──────────────────────────────────────────────────────────────────
Owns everything that outlives a single function call:

  · UpdateState machine guarding every UI surface (§15) — invalid
    transitions raise instead of letting widgets and reality drift
  · pending.json / update-success.json install-confirmation markers
    (§13): the independent updater writes pending, the NEW build
    confirms after startup, the updater waits for that confirmation
  · update-state.json auto-check cache: lastCheckAt (24 h throttle),
    lastKnownVersion, dismissedVersion (§19)
  · updates/update.log audit trail (§26) — never logs secrets
  · backup/ + rollback helpers (§14): "a failed update must never be
    worse than no update"

All paths derive from config.settings.APP_DIR at call time so tests can
rebind the data root.
"""
from __future__ import annotations

import datetime as _dt
import enum
import json
import shutil
import time
import uuid
from pathlib import Path

from config import settings as _settings

AUTO_CHECK_INTERVAL_SEC = 24 * 3600
DEFAULT_CONFIRM_TIMEOUT_SEC = 90.0


# ── State machine (§15) ──────────────────────────────────────

class UpdateState(enum.Enum):
    IDLE = "idle"
    CHECKING = "checking"
    NO_UPDATE = "no_update"
    UPDATE_AVAILABLE = "update_available"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    READY_TO_INSTALL = "ready_to_install"
    WAITING_APP_EXIT = "waiting_app_exit"
    INSTALLING = "installing"
    VERIFYING_INSTALL = "verifying_install"
    ROLLING_BACK = "rolling_back"
    SUCCESS = "success"
    FAILED = "failed"


_IDLE, _CHECKING = UpdateState.IDLE, UpdateState.CHECKING
_NO_UPDATE, _AVAILABLE = UpdateState.NO_UPDATE, UpdateState.UPDATE_AVAILABLE
_DOWNLOADING, _VERIFYING = UpdateState.DOWNLOADING, UpdateState.VERIFYING
_READY, _WAIT_EXIT = UpdateState.READY_TO_INSTALL, UpdateState.WAITING_APP_EXIT
_INSTALLING, _VERIFY_INSTALL = UpdateState.INSTALLING, UpdateState.VERIFYING_INSTALL
_ROLLBACK, _SUCCESS, _FAILED = (UpdateState.ROLLING_BACK, UpdateState.SUCCESS,
                                UpdateState.FAILED)

_ALLOWED_TRANSITIONS: dict[UpdateState, frozenset] = {
    _IDLE: frozenset({_CHECKING}),
    _CHECKING: frozenset({_NO_UPDATE, _AVAILABLE, _FAILED}),
    _NO_UPDATE: frozenset({_CHECKING}),
    _AVAILABLE: frozenset({_CHECKING, _DOWNLOADING}),
    _DOWNLOADING: frozenset({_VERIFYING, _AVAILABLE, _FAILED}),
    _VERIFYING: frozenset({_READY, _FAILED}),
    _READY: frozenset({_WAIT_EXIT, _DOWNLOADING, _AVAILABLE, _FAILED}),
    _WAIT_EXIT: frozenset({_INSTALLING, _FAILED}),
    _INSTALLING: frozenset({_VERIFY_INSTALL, _FAILED}),
    _VERIFY_INSTALL: frozenset({_SUCCESS, _FAILED, _ROLLBACK}),
    _ROLLBACK: frozenset({_FAILED}),
    _SUCCESS: frozenset({_IDLE}),
    _FAILED: frozenset({_IDLE, _CHECKING, _DOWNLOADING, _AVAILABLE}),
}


class UpdateFlow:
    """Guarded FSM; UI widgets are driven exclusively by transitions."""

    def __init__(self, initial: UpdateState = UpdateState.IDLE):
        self._state = initial

    @property
    def state(self) -> UpdateState:
        return self._state

    def transition(self, new_state: UpdateState) -> UpdateState:
        allowed = _ALLOWED_TRANSITIONS[self._state]
        if new_state not in allowed:
            raise ValueError(
                f"illegal update transition: {self._state.value} -> "
                f"{new_state.value} (allowed: "
                f"{sorted(s.value for s in allowed)})")
        append_update_log(
            f"state: {self._state.value} -> {new_state.value}")
        self._state = new_state
        return new_state


# ── Paths ────────────────────────────────────────────────────

def update_root() -> Path:
    return Path(_settings.APP_DIR) / "updates"


def download_dir(version: str) -> Path:
    return update_root() / str(version)


def backup_dir(version: str) -> Path:
    return update_root() / "backup" / str(version)


def runtime_root() -> Path:
    return update_root() / "runtime"


def pending_path() -> Path:
    return update_root() / "pending.json"


def success_path() -> Path:
    return update_root() / "update-success.json"


def check_state_path() -> Path:
    return update_root() / "update-state.json"


def log_path() -> Path:
    return update_root() / "update.log"


# ── Audit log (§26) ──────────────────────────────────────────

def append_update_log(message: str) -> None:
    """Append a timestamped line to the update audit log.

    Never throws and never logs secrets — callers only pass versions,
    paths, codes and sizes.
    """
    try:
        root = update_root()
        root.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path(), "a", encoding="utf-8") as fh:
            fh.write(f"[{stamp}] {message}\n")
    except OSError:
        pass


# ── Install confirmation markers (§13) ───────────────────────

def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_pending(from_version: str, to_version: str,
                  nonce: str | None = None) -> dict:
    """Called by the updater right before launching the new build."""
    payload = {
        "from": str(from_version),
        "to": str(to_version),
        "startedAt": _now_iso(),
        "nonce": nonce or uuid.uuid4().hex,
    }
    root = update_root()
    root.mkdir(parents=True, exist_ok=True)
    with open(pending_path(), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    append_update_log(
        f"pending update marker written: {from_version} -> {to_version} "
        f"(nonce={payload['nonce'][:8]}…)")
    return payload


def read_pending() -> dict | None:
    try:
        with open(pending_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def clear_pending() -> None:
    for path in (pending_path(), success_path()):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def confirm_pending_update(current_version: str) -> bool:
    """Called by the NEW build shortly after startup (doc §13).

    When a pending marker targets exactly this version, write the
    success marker — the updater polls for it, treats the upgrade as
    verified, cleans up and never rolls back.
    """
    pending = read_pending()
    if not pending or str(pending.get("to")) != str(current_version):
        return False
    payload = dict(pending)
    payload["confirmedAt"] = _now_iso()
    payload["confirmedVersion"] = str(current_version)
    try:
        update_root().mkdir(parents=True, exist_ok=True)
        with open(success_path(), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except OSError:
        return False
    append_update_log(
        f"update confirmed by new build: v{current_version}")
    return True


# ── Auto-check cache (§19) ───────────────────────────────────

def load_check_state() -> dict:
    try:
        with open(check_state_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_check_state(data: dict) -> None:
    try:
        update_root().mkdir(parents=True, exist_ok=True)
        with open(check_state_path(), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except OSError:
        pass


def mark_checked(known_version: str | None = None) -> None:
    data = load_check_state()
    data["lastCheckAt"] = _now_iso()
    if known_version:
        data["lastKnownVersion"] = str(known_version)
    save_check_state(data)


def _parse_iso(text: str) -> float | None:
    try:
        return _dt.datetime.fromisoformat(
            str(text).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def should_auto_check(now: float | None = None) -> bool:
    """True when the last successful check is older than 24 h (or absent)."""
    last = _parse_iso(load_check_state().get("lastCheckAt", ""))
    if last is None:
        return True
    now = time.time() if now is None else now
    return (now - last) >= AUTO_CHECK_INTERVAL_SEC


def is_dismissed(version: str) -> bool:
    return str(load_check_state().get("dismissedVersion", "")) == str(version)


def dismiss(version: str) -> None:
    data = load_check_state()
    data["dismissedVersion"] = str(version)
    save_check_state(data)


# ── Backup / rollback (§14) ──────────────────────────────────

def backup_file(src: Path, version: str) -> Path | None:
    """Copy a program file into updates/backup/<version>/ before the
    installer touches it.  Returns the backup path (None on failure —
    rollback then degrades to skipping)."""
    try:
        dest_dir = backup_dir(version)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / Path(src).name
        shutil.copy2(src, dest)
        append_update_log(f"backup written: {src} -> {dest}")
        return dest
    except OSError as exc:
        append_update_log(f"backup FAILED for {src}: {exc}")
        return None


def restore_backup(version: str, file_name: str, dest: Path) -> bool:
    try:
        src = backup_dir(version) / file_name
        if not src.is_file():
            append_update_log(f"restore FAILED: no backup {src}")
            return False
        shutil.copy2(src, dest)
        append_update_log(f"restored {file_name} from backup v{version}")
        return True
    except OSError as exc:
        append_update_log(f"restore FAILED: {exc}")
        return False


# ── Cleanup (§13/§30) ────────────────────────────────────────

def purge_runtime_dirs(keep: Path | None = None) -> None:
    """Delete updater runtime copies (updater copies itself to a random
    runtime dir before running so the installer can overwrite the app
    dir).  A running updater cannot delete its own exe — leftovers are
    purged by the next app start."""
    try:
        runtime = runtime_root()
        if not runtime.is_dir():
            return
        keep = keep.resolve() if keep is not None else None
        for child in runtime.iterdir():
            if keep is not None:
                try:
                    if child.resolve() == keep or keep.is_relative_to(child.resolve()):
                        continue
                except OSError:
                    continue
            shutil.rmtree(child, ignore_errors=True)
    except OSError:
        pass


def cleanup_after_success(target_version: str | None = None,
                          from_version: str | None = None,
                          keep_runtime: Path | None = None) -> None:
    """Post-confirmation cleanup: remove the downloaded package, the
    rollback backup, all confirmation markers and runtime copies."""
    versions = {str(v) for v in (target_version, from_version) if v}
    for version in versions:
        shutil.rmtree(download_dir(version), ignore_errors=True)
        if from_version and version == str(from_version):
            shutil.rmtree(backup_dir(version), ignore_errors=True)
    clear_pending()
    purge_runtime_dirs(keep=keep_runtime)
    append_update_log("cleanup after successful update done")
