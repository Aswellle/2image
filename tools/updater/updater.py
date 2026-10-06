#!/usr/bin/env python3
"""
tools/updater/updater.py — standalone Windows update runner
────────────────────────────────────────────────────────────
Packaged as ``2image_updater.exe`` (tools/updater/updater.spec).  The
app never modifies its own exe; the updater takes over after the app
exits.  To survive the installer overwriting the app directory, the
parent process first copies itself into a random runtime dir and the
real work happens from that copy:

    2image.exe
        └─ spawns 2image_updater.exe (parent)
             └─ copies itself → updates/runtime/<id>/2image_updater.exe
                  (child, --runtime flag):
                      1  validate arguments (installer path, SHA-256)
                      2  wait for the app process to exit
                      3  re-verify installer SHA-256          → exit 3
                      4  back up the old exe                  (rollback kit)
                      5  silent in-place Inno Setup install   → exit 4
                      6  verify the new exe exists
                      7  write pending.json, launch the new build
                      8  wait for update-success.json         → else rollback
                      9  success: cleanup | failure: restore backup, relaunch old

Exit codes: 0 ok · 2 bad args · 3 hash mismatch · 4 install failed
            5 post-verify failure (rolled back) · 6 rollback failed

Everything is logged to ~/2image/updates/update.log; fatal states are
surfaced with a MessageBoxW because the build is windowed.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

if not getattr(sys, "frozen", False):
    # Source run (dev/tests): make the repo packages importable.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.updater import installer as upd_installer   # noqa: E402
from services.updater import state as upd_state           # noqa: E402

EXIT_OK = 0
EXIT_ARGS = 2
EXIT_HASH = 3
EXIT_INSTALL = 4
EXIT_ROLLBACK = 5
EXIT_ROLLBACK_FAILED = 6

APP_EXE = upd_installer.APP_EXE_NAME
_PROCESS_SYNCHRONIZE = 0x00100000
_PROCESS_QUERY_LIMITED = 0x1000


# ── small helpers ────────────────────────────────────────────

def _fatal(title: str, text: str) -> None:
    """Show a blocking error dialog (windowed build: no console).

    Source runs (dev/tests) have a console and no user watching for
    dialogs — log to stderr instead so nothing can block on a hidden
    MessageBox.
    """
    if not getattr(sys, "frozen", False):
        try:
            print(f"[updater] {title}: {text}", file=sys.stderr)
        except OSError:
            pass
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)  # MB_ICONERROR
    except Exception:
        pass


def sha256_of_file(path: Path, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def wait_for_pid(pid: int, timeout: float = 180.0,
                 poll: float = 0.5) -> bool:
    """Wait until ``pid`` exits; True=exited, False=timed out.

    Uses WaitForSingleObject on a PROCESS_SYNCHRONIZE handle; falls
    back to polling PROCESS_QUERY_LIMITED_INFORMATION for pids we may
    not synchronize on.  pid <= 0 counts as already exited.
    """
    if pid <= 0:
        return True
    if sys.platform != "win32":
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                Path(f"/proc/{pid}").exists()
            except OSError:
                return True
            time.sleep(poll)
        return False

    import ctypes
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(_PROCESS_SYNCHRONIZE, False, pid)
    if handle:
        try:
            code = kernel32.WaitForSingleObject(handle, int(timeout * 1000))
            if code == 0x00000000:          # WAIT_OBJECT_0 — exited
                return True
            if code == 0x00000102:          # WAIT_TIMEOUT — still running
                return False
            # Unexpected wait error → fall through to polling.
        finally:
            kernel32.CloseHandle(handle)
    return _poll_pid(kernel32, pid, time.monotonic() + timeout, poll)


def _poll_pid(kernel32, pid: int, deadline: float, poll: float) -> bool:
    while time.monotonic() < deadline:
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED, False, pid)
        if not handle:
            return True   # gone (or access denied → cannot wait forever)
        kernel32.CloseHandle(handle)
        time.sleep(poll)
    return False


# ── child flow steps ─────────────────────────────────────────

def verify_installer(installer: Path, expected_sha: str) -> bool:
    actual = sha256_of_file(installer)
    ok = actual.lower() == expected_sha.lower()
    upd_state.append_update_log(
        f"installer re-verify: expected={expected_sha[:16]}… "
        f"actual={actual[:16]}… ok={ok}")
    return ok


def wait_for_confirmation(timeout: float, poll: float = 1.0) -> bool:
    """Poll for the success marker written by the new build."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if upd_state.success_path().is_file():
                return True
        except OSError:
            pass
        time.sleep(poll)
    return False


def rollback(args, new_proc: subprocess.Popen | None) -> int:
    """Restore the backed-up old exe and relaunch it (doc §14).

    A failed update must never be worse than no update: the user ends
    up back on the previous working build.
    """
    upd_state.append_update_log("ROLLBACK initiated")
    if new_proc is not None:
        try:
            new_proc.kill()
            new_proc.wait(timeout=10)
            upd_state.append_update_log("new build process terminated")
        except Exception as exc:
            upd_state.append_update_log(f"kill new build failed: {exc}")
    install_dir = Path(args.install_dir)
    restored = upd_state.restore_backup(args.from_version, APP_EXE,
                                        install_dir / APP_EXE)
    if not restored:
        upd_state.append_update_log("rollback FAILED — old exe unrestored")
        _fatal("2image update",
               "Update failed and rollback could not restore the old "
               "version. A backup is kept at:\n"
               f"{upd_state.backup_dir(args.from_version)}")
        return EXIT_ROLLBACK_FAILED
    old_exe = install_dir / APP_EXE
    if old_exe.is_file():
        try:
            upd_installer.launch_detached(old_exe)
            upd_state.append_update_log("old build relaunched after rollback")
        except OSError as exc:
            upd_state.append_update_log(f"relaunch old build failed: {exc}")
    _fatal("2image update",
           "The update did not complete.\nThe previous version has been "
           "restored and restarted.")
    return EXIT_ROLLBACK


def run_child(args) -> int:
    upd_state.append_update_log(
        f"updater child started: {args.from_version} -> "
        f"{args.target_version} (parent pid {args.parent_pid})")

    # 1 · validate arguments
    installer = Path(args.installer)
    install_dir = Path(args.install_dir)
    if len(args.expected_sha256) != 64:
        upd_state.append_update_log("bad expected sha256 length")
        _fatal("2image update", "Updater arguments are invalid.")
        return EXIT_ARGS
    if not installer.is_file() or not install_dir.is_dir():
        upd_state.append_update_log(
            f"missing installer/install dir: {installer} / {install_dir}")
        _fatal("2image update", "Updater arguments are invalid.")
        return EXIT_ARGS

    # 2 · wait for the app to exit (never force-kill it)
    started = time.monotonic()
    if not wait_for_pid(args.parent_pid, timeout=args.wait_timeout):
        upd_state.append_update_log("parent did not exit in time — aborting")
        return EXIT_INSTALL
    upd_state.append_update_log(
        f"parent exited after {time.monotonic() - started:.1f}s")

    # 3 · re-verify the package right before executing it
    if not verify_installer(installer, args.expected_sha256):
        _fatal("2image update",
               "The downloaded installer failed verification and will "
               "not be run.")
        return EXIT_HASH

    # 4 · backup the old exe (rollback kit)
    parent_exe = Path(args.parent_exe) if args.parent_exe else (
        install_dir / APP_EXE)
    if parent_exe.is_file():
        upd_state.backup_file(parent_exe, args.from_version)

    # 5 · silent in-place install; exit code 0 is the only success
    cmd = upd_installer.build_installer_command(
        installer, install_dir, upd_state.log_path())
    upd_state.append_update_log(f"running installer: {installer.name}")
    try:
        rc = upd_installer.run_installer(cmd)
    except Exception as exc:
        upd_state.append_update_log(f"installer launch failed: {exc}")
        return rollback(args, None)
    upd_state.append_update_log(f"installer exit code: {rc}")
    if rc != 0:
        return rollback(args, None)

    # 6 · the new exe must exist after a "successful" install
    new_exe = install_dir / APP_EXE
    if not new_exe.is_file():
        upd_state.append_update_log("post-install: new exe missing")
        return rollback(args, None)

    # 7 · hand over: pending marker + launch the new build
    upd_state.write_pending(args.from_version, args.target_version)
    try:
        new_proc = upd_installer.launch_detached(new_exe)
    except OSError as exc:
        upd_state.append_update_log(f"launch new build failed: {exc}")
        return rollback(args, None)

    # 8 · the new build must confirm itself within the timeout
    if wait_for_confirmation(args.confirm_timeout):
        upd_state.append_update_log(
            f"update confirmed: v{args.target_version} is running")
        upd_state.cleanup_after_success(
            target_version=args.target_version,
            from_version=args.from_version,
            keep_runtime=Path(sys.executable if getattr(sys, "frozen", False)
                              else __file__).parent)
        return EXIT_OK

    upd_state.append_update_log(
        "new build did not confirm in time — rolling back")
    return rollback(args, new_proc)


# ── entry points ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="2image_updater", description="2image in-app update runner")
    p.add_argument("--installer", required=True,
                   help="path of the downloaded installer exe")
    p.add_argument("--expected-sha256", required=True,
                   help="SHA-256 of the installer from the manifest")
    p.add_argument("--install-dir", required=True,
                   help="current installation directory")
    p.add_argument("--parent-pid", type=int, default=0,
                   help="pid of the running app to wait for")
    p.add_argument("--parent-exe", default="",
                   help="path of the old app exe (backup source)")
    p.add_argument("--from-version", required=True)
    p.add_argument("--target-version", required=True)
    p.add_argument("--wait-timeout", type=float, default=180.0)
    p.add_argument("--confirm-timeout", type=float,
                   default=upd_state.DEFAULT_CONFIRM_TIMEOUT_SEC)
    p.add_argument("--runtime", action="store_true",
                   help=argparse.SUPPRESS)  # child marker
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    frozen = getattr(sys, "frozen", False)

    if args.runtime or not frozen:
        # Source run (dev/tests) or already the runtime copy: do the work.
        return run_child(args)

    # Parent: copy self into a private runtime dir and re-exec from
    # there, so the installer can freely overwrite the app directory.
    runtime_dir = upd_state.runtime_root() / uuid.uuid4().hex
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        runtime_exe = runtime_dir / Path(sys.executable).name
        shutil.copy2(sys.executable, runtime_exe)
        upd_state.append_update_log(
            f"updater copied to runtime: {runtime_exe}")
        upd_installer.launch_detached(runtime_exe)
    except OSError as exc:
        upd_state.append_update_log(
            f"runtime copy failed ({exc}); running in place")
        return run_child([a for a in sys.argv[1:]] + ["--runtime"])
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
