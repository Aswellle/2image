"""Standalone updater script (tools/updater/updater.py): argument
validation, pre-execution hash re-verification, confirmation wait and
rollback behavior — the installer itself is never executed here."""
import hashlib
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
_SPEC_PATH = ROOT / "tools" / "updater" / "updater.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("updater_script",
                                                  _SPEC_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def upd():
    return _load_module()


def _args(tmp_path, **over):
    ns = MagicMock()
    ns.installer = str(tmp_path / "pkg.exe")
    ns.expected_sha256 = "0" * 64
    ns.install_dir = str(tmp_path / "install")
    ns.parent_pid = 0
    ns.parent_exe = ""
    ns.from_version = "2.6.0"
    ns.target_version = "2.7.0"
    ns.wait_timeout = 1.0
    ns.confirm_timeout = 1.0
    for key, value in over.items():
        setattr(ns, key, value)
    return ns


# ── helpers ──────────────────────────────────────────────────

def test_sha256_of_file_matches_hashlib(upd, tmp_path):
    p = tmp_path / "blob.bin"
    p.write_bytes(b"x" * 5000)
    assert upd.sha256_of_file(p) == hashlib.sha256(b"x" * 5000).hexdigest()


def test_wait_for_pid_zero_is_already_exited(upd):
    assert upd.wait_for_pid(0, timeout=0.1) is True


def test_wait_for_pid_nonexistent_exits_fast(upd):
    assert upd.wait_for_pid(4_000_000, timeout=1.0) is True


def test_wait_for_confirmation_checks_success_marker(upd):
    from services.updater import state as st
    assert upd.wait_for_confirmation(0.1, poll=0.05) is False
    st.success_path().parent.mkdir(parents=True, exist_ok=True)
    st.success_path().write_text("{}", encoding="utf-8")
    try:
        assert upd.wait_for_confirmation(1.0, poll=0.05) is True
    finally:
        st.success_path().unlink(missing_ok=True)


# ── child flow ───────────────────────────────────────────────

def test_child_rejects_bad_sha_length(upd, tmp_path):
    args = _args(tmp_path, expected_sha256="abc")
    assert upd.run_child(args) == upd.EXIT_ARGS


def test_child_rejects_missing_installer(upd, tmp_path):
    args = _args(tmp_path)
    assert upd.run_child(args) == upd.EXIT_ARGS


def test_child_refuses_tampered_installer_before_running_it(upd, tmp_path):
    (tmp_path / "install").mkdir(parents=True)
    pkg = tmp_path / "pkg.exe"
    pkg.write_bytes(b"tampered-content")
    args = _args(tmp_path)  # expected sha is all-zero → mismatch
    launched = []
    monkey = pytest.MonkeyPatch()
    monkey.setattr(upd.upd_installer, "run_installer",
                   lambda cmd: launched.append(cmd) or 0)
    try:
        assert upd.run_child(args) == upd.EXIT_HASH
        assert launched == []          # installer never executed
    finally:
        monkey.undo()


def test_child_rollback_restores_old_exe_on_install_failure(upd, tmp_path):
    from services.updater import state as st
    install_dir = tmp_path / "install"
    install_dir.mkdir(parents=True)
    old_exe = install_dir / "2image.exe"
    old_exe.write_bytes(b"old-build")
    pkg = tmp_path / "pkg.exe"
    pkg.write_bytes(b"payload")
    sha = hashlib.sha256(b"payload").hexdigest()

    args = _args(tmp_path, parent_exe=str(old_exe))
    args.expected_sha256 = sha

    monkey = pytest.MonkeyPatch()
    relaunched = []
    monkey.setattr(upd.upd_installer, "run_installer", lambda cmd: 1)  # fail
    monkey.setattr(upd.upd_installer, "launch_detached",
                   lambda exe, args=None: relaunched.append(Path(exe)))
    monkey.setattr(upd, "_fatal", lambda *a, **k: None)
    try:
        assert upd.run_child(args) == upd.EXIT_ROLLBACK
        assert old_exe.read_bytes() == b"old-build"
        assert relaunched == [old_exe]
    finally:
        monkey.undo()


def test_child_waits_for_confirmation_and_cleans_up(upd, tmp_path):
    from services.updater import state as st
    install_dir = tmp_path / "install"
    install_dir.mkdir(parents=True)
    old_exe = install_dir / "2image.exe"
    old_exe.write_bytes(b"old-build")
    pkg = tmp_path / "pkg.exe"
    pkg.write_bytes(b"payload")
    sha = hashlib.sha256(b"payload").hexdigest()

    args = _args(tmp_path, parent_exe=str(old_exe))
    args.expected_sha256 = sha
    args.confirm_timeout = 2.0

    new_proc = MagicMock()

    def fake_launch(exe, cmd_args=None):
        # emulate the new build writing its success marker
        st.success_path().parent.mkdir(parents=True, exist_ok=True)
        st.write_pending("2.6.0", "2.7.0")
        st.confirm_pending_update("2.7.0")
        return new_proc

    monkey = pytest.MonkeyPatch()
    killed = []
    monkey.setattr(upd.upd_installer, "run_installer", lambda cmd: 0)
    monkey.setattr(upd.upd_installer, "launch_detached",
                   lambda exe, cmd_args=None: fake_launch(exe, cmd_args))
    try:
        assert upd.run_child(args) == upd.EXIT_OK
        assert st.read_pending() is None          # cleaned up
        assert not st.success_path().exists()
        assert killed == []
    finally:
        monkey.undo()


def test_child_rolls_back_when_new_build_never_confirms(upd, tmp_path):
    from services.updater import state as st
    install_dir = tmp_path / "install"
    install_dir.mkdir(parents=True)
    old_exe = install_dir / "2image.exe"
    old_exe.write_bytes(b"old-build")
    pkg = tmp_path / "pkg.exe"
    pkg.write_bytes(b"payload")
    args = _args(tmp_path, parent_exe=str(old_exe))
    args.expected_sha256 = hashlib.sha256(b"payload").hexdigest()
    args.confirm_timeout = 0.3

    new_proc = MagicMock()
    new_proc.kill = lambda: None
    new_proc.wait = lambda timeout=None: 0

    monkey = pytest.MonkeyPatch()
    relaunched = []
    monkey.setattr(upd.upd_installer, "run_installer", lambda cmd: 0)
    monkey.setattr(upd.upd_installer, "launch_detached",
                   lambda exe, args=None: relaunched.append(Path(exe)))
    monkey.setattr(upd, "_fatal", lambda *a, **k: None)
    # pretend the installer produced the new exe but it never confirmed
    monkey.setattr(upd.upd_installer, "APP_EXE_NAME", "2image.exe")
    try:
        (install_dir / "2image.exe").write_bytes(b"old-build")  # unchanged
        rc = upd.run_child(args)
        assert rc == upd.EXIT_ROLLBACK
        # call 1: launch the (never-confirming) new build; call 2: the
        # rollback relaunching the restored old exe
        assert relaunched == [old_exe, old_exe]
    finally:
        monkey.undo()
