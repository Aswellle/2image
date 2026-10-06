"""State machine transitions, pending/confirm markers, auto-check
throttle, dismiss, backup/rollback helpers (§13/§14/§15/§19)."""
import datetime as dt
import time

import pytest

from services.updater import state as st
from services.updater.state import UpdateFlow, UpdateState


# ── state machine ────────────────────────────────────────────

def test_happy_path_transitions():
    flow = UpdateFlow()
    for step in (UpdateState.CHECKING, UpdateState.UPDATE_AVAILABLE,
                 UpdateState.DOWNLOADING, UpdateState.VERIFYING,
                 UpdateState.READY_TO_INSTALL, UpdateState.WAITING_APP_EXIT,
                 UpdateState.INSTALLING, UpdateState.VERIFYING_INSTALL,
                 UpdateState.SUCCESS, UpdateState.IDLE):
        flow.transition(step)
    assert flow.state is UpdateState.IDLE


def test_illegal_transition_raises_and_keeps_state():
    flow = UpdateFlow()
    with pytest.raises(ValueError):
        flow.transition(UpdateState.SUCCESS)
    assert flow.state is UpdateState.IDLE


def test_failure_and_retry_paths():
    flow = UpdateFlow()
    flow.transition(UpdateState.CHECKING)
    flow.transition(UpdateState.FAILED)
    flow.transition(UpdateState.CHECKING)
    flow.transition(UpdateState.NO_UPDATE)
    flow.transition(UpdateState.CHECKING)
    flow.transition(UpdateState.UPDATE_AVAILABLE)
    # user cancels mid-download
    flow.transition(UpdateState.DOWNLOADING)
    flow.transition(UpdateState.FAILED)
    flow.transition(UpdateState.UPDATE_AVAILABLE)


# ── pending / confirm markers ────────────────────────────────

def test_pending_write_read_roundtrip():
    payload = st.write_pending("2.6.0", "2.7.0")
    assert payload["to"] == "2.7.0" and payload["nonce"]
    read = st.read_pending()
    assert read is not None and read["from"] == "2.6.0"


def test_confirm_ignores_other_versions():
    st.write_pending("2.6.0", "2.7.0")
    assert st.confirm_pending_update("2.6.0") is False
    assert st.success_path().exists() is False
    assert st.confirm_pending_update("2.7.0") is True
    assert st.success_path().is_file()


def test_confirm_without_pending_is_noop():
    assert st.confirm_pending_update("2.7.0") is False


def test_clear_pending_removes_both_markers():
    st.write_pending("2.6.0", "2.7.0")
    st.confirm_pending_update("2.7.0")
    st.clear_pending()
    assert st.read_pending() is None
    assert not st.success_path().exists()


# ── auto-check cache ─────────────────────────────────────────

def test_should_auto_check_without_state_file():
    assert st.should_auto_check() is True


def test_should_auto_check_throttled_after_recent_check():
    st.mark_checked("2.7.0")
    assert st.should_auto_check() is False


def test_should_auto_check_allows_after_24h():
    st.mark_checked("2.7.0")
    data = st.load_check_state()
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=25)
    data["lastCheckAt"] = old.strftime("%Y-%m-%dT%H:%M:%SZ")
    st.save_check_state(data)
    assert st.should_auto_check() is True


def test_dismiss_roundtrip():
    st.dismiss("2.7.0")
    assert st.is_dismissed("2.7.0") is True
    assert st.is_dismissed("2.7.1") is False


# ── backup / restore ─────────────────────────────────────────

def test_backup_and_restore_roundtrip(tmp_path):
    src = tmp_path / "2image.exe"
    src.write_bytes(b"old-build-bytes")
    backup = st.backup_file(src, "2.6.0")
    assert backup is not None and backup.is_file()

    src.write_bytes(b"corrupted-by-new-build")
    assert st.restore_backup("2.6.0", "2image.exe", src) is True
    assert src.read_bytes() == b"old-build-bytes"


def test_restore_missing_backup_fails(tmp_path):
    dest = tmp_path / "2image.exe"
    assert st.restore_backup("9.9.9", "2image.exe", dest) is False


# ── cleanup ──────────────────────────────────────────────────

def test_cleanup_after_success_removes_everything():
    st.write_pending("2.6.0", "2.7.0")
    st.confirm_pending_update("2.7.0")
    dl_dir = st.download_dir("2.7.0")
    dl_dir.mkdir(parents=True, exist_ok=True)
    (dl_dir / "pkg.exe").write_bytes(b"x")
    backup = st.backup_dir("2.6.0")
    backup.mkdir(parents=True, exist_ok=True)
    (backup / "2image.exe").write_bytes(b"old")

    st.cleanup_after_success(target_version="2.7.0", from_version="2.6.0")
    assert not dl_dir.exists()
    assert not backup.exists()
    assert st.read_pending() is None


def test_purge_runtime_dirs_keeps_running_dir(tmp_path):
    running = st.runtime_root() / "aaaa"
    stale = st.runtime_root() / "bbbb"
    for d in (running, stale):
        d.mkdir(parents=True, exist_ok=True)
        (d / "2image_updater.exe").write_bytes(b"x")
    st.purge_runtime_dirs(keep=running / "2image_updater.exe")
    assert running.is_dir()
    assert not stale.exists()
