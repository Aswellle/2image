"""Installer command construction + install-mode detection (§9/§10):
argument arrays only (never shell=True), silent in-place flags."""
import sys
from pathlib import Path

from services.updater import installer as ins


def test_command_is_argument_array_with_silent_flags():
    cmd = ins.build_installer_command(
        Path("C:/pkg/2image-setup-v2.7.0.exe"),
        Path("C:/Users/u/AppData/Local/2image"),
        Path("C:/Users/u/2image/updates/update.log"))
    assert isinstance(cmd, list)
    assert cmd[0].endswith("2image-setup-v2.7.0.exe")
    assert "/VERYSILENT" in cmd
    assert "/SUPPRESSMSGBOXES" in cmd
    assert "/NORESTART" in cmd
    assert "/CLOSEAPPLICATIONS" in cmd
    # restart is the updater's job, not the installer's
    assert "/NORESTARTAPPLICATIONS" in cmd
    assert "/RESTARTAPPLICATIONS" not in cmd
    assert any(str(c).startswith("/DIR=") for c in cmd)
    assert any(str(c).startswith("/LOG=") for c in cmd)
    # every argument is a plain string; no shell invocation anywhere
    assert all(isinstance(c, str) for c in cmd)


def test_detect_install_mode_false_in_source_runs():
    assert ins.detect_install_mode() is False


def test_detect_install_mode_true_with_unins000(tmp_path, monkeypatch):
    (tmp_path / "unins000.exe").write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "2image.exe"))
    assert ins.detect_install_mode() is True


def test_detect_install_mode_false_portable(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "2image.exe"))
    assert ins.detect_install_mode() is False
