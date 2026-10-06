"""
services/updater/installer.py — Inno Setup silent install helpers
─────────────────────────────────────────────────────────────────
The installer is always launched as an argument array (never
shell=True) so paths with spaces/Chinese characters survive intact.
The fixed AppId in installer/template.iss makes Inno reuse the same
install instance: the new build replaces the old program files
in-place while everything under ~/2image (config, history, images)
stays untouched.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from services.updater.errors import UpdateError, UpdateErrorCode

UNINSTALLER_NAME = "unins000.exe"
APP_EXE_NAME = "2image.exe"
INSTALLER_TIMEOUT = 3600.0

_CREATE_NO_WINDOW = 0x08000000


def detect_install_mode() -> bool:
    """True for an installed (Inno Setup) build: the Inno uninstaller
    unins000.exe sits next to the running executable.  Portable runs
    and source runs return False."""
    if not getattr(sys, "frozen", False):
        return False
    try:
        return Path(sys.executable).parent.joinpath(UNINSTALLER_NAME).exists()
    except OSError:
        return False


def detect_install_dir() -> Path:
    """Directory of the running executable (= current install dir)."""
    return Path(sys.executable).parent


def build_installer_command(installer: Path, install_dir: Path,
                            log_file: Path) -> list[str]:
    """Silent in-place upgrade command line (doc §10).

    /CLOSEAPPLICATIONS lets Inno close a still-running app instance,
    /NORESTARTAPPLICATIONS keeps restart control with the updater
    (it launches the new build itself after verifying the install).
    """
    return [
        str(installer),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/CLOSEAPPLICATIONS",
        "/NORESTARTAPPLICATIONS",
        f"/DIR={install_dir}",
        f"/LOG={log_file}",
    ]


def run_installer(cmd: list[str], timeout: float = INSTALLER_TIMEOUT) -> int:
    """Run the installer to completion and return its exit code.

    Exit code 0 means success; anything else is an unfinished install
    and must trigger the failure path.  Raises
    UpdateError(INSTALLER_LAUNCH_FAILED) when the installer binary
    cannot be started at all.
    """
    creationflags = _CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.run(cmd, timeout=timeout, close_fds=True,
                              creationflags=creationflags)
    except FileNotFoundError as exc:
        raise UpdateError(
            UpdateErrorCode.INSTALLER_LAUNCH_FAILED,
            f"installer not found: {cmd[0] if cmd else ''}") from exc
    except PermissionError as exc:
        raise UpdateError(
            UpdateErrorCode.INSTALLER_LAUNCH_FAILED,
            f"installer launch denied: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise UpdateError(
            UpdateErrorCode.INSTALL_FAILED,
            f"installer timed out after {timeout:.0f}s") from exc
    return proc.returncode


def launch_detached(exe: Path, args: list[str] | None = None) -> subprocess.Popen:
    """Start a process fully detached from this one (survives our exit)."""
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen([str(exe)] + [str(a) for a in (args or [])],
                            creationflags=flags, close_fds=True)
