"""
ui/about_dialog.py — About window + state-machine driven update flow
─────────────────────────────────────────────────────────────────────
Every widget change funnels through UpdateFlow.transition() so UI state
can never drift from what the flow is actually doing (a re-enabled
button with a live download behind it is exactly the bug class this
prevents).

Flow: check (update.json manifest on GitHub Releases) → show the new
version → download the installer (.partial → size → SHA-256 → atomic
rename, progress + cancellable) → confirm install → hand over to the
independent updater (2image_updater.exe) which waits for this app to
exit, re-verifies the package, installs in-place over the old build and
rolls back on any failure.  Portable runs download the installer and
choose between running it and opening the releases page.

All network/disk work happens on daemon threads; UI only receives
callbacks marshalled through root.after.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

from config.fonts import F
from config.theme import DARK_THEME as C
from config.i18n import _

from services.updater import (
    RELEASES_PAGE,
    UpdateError,
    UpdateErrorCode,
    UpdateFlow,
    UpdateState,
    append_update_log,
    get_current_version,
)
from services.updater import downloader as _downloader
from services.updater import installer as _installer
from services.updater import state as _state
from services.generation.cancellation import CancellationToken
from services.generation.errors import GenerationCancelled

_ERR_KEYS = {
    UpdateErrorCode.NETWORK_ERROR: "upd_err_network",
    UpdateErrorCode.HTTP_ERROR: "upd_err_http",
    UpdateErrorCode.MANIFEST_INVALID: "upd_err_manifest",
    UpdateErrorCode.VERSION_INVALID: "upd_err_version",
    UpdateErrorCode.SIZE_MISMATCH: "upd_err_size",
    UpdateErrorCode.HASH_MISMATCH: "upd_err_hash",
    UpdateErrorCode.INSTALLER_LAUNCH_FAILED: "upd_err_launch",
    UpdateErrorCode.INSTALL_FAILED: "upd_err_install",
    UpdateErrorCode.CANCELLED: "upd_err_cancel",
}


def _err_text(code: UpdateErrorCode) -> str:
    key = _ERR_KEYS.get(code, "upd_err_unknown")
    return _(key)


class AboutDialog(tk.Toplevel):
    """About 2image: version info + update check + download & install."""

    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.app = parent_app
        self.root = parent_app.root
        self.title(_("about_title"))
        self.geometry("560x560")
        self.resizable(False, True)
        self.configure(bg=C["bg"])
        self.transient(self.root)

        self._flow = UpdateFlow()
        self._token: CancellationToken | None = None
        self._manifest = None            # UpdateManifest | None
        self._package_path: Path | None = None

        self._build()
        self._fill_version()
        self._apply_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.grab_set()

    # ── layout ───────────────────────────────────────────────
    def _build(self):
        hdr = tk.Frame(self, bg=C["acc"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=_("about_title"), font=F["title"],
                 bg=C["acc"], fg="white").pack(anchor="w", padx=20, pady=14)

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=20)

        self._ver_lbl = tk.Label(body, text="", font=F["h2"],
                                 bg=C["bg"], fg=C["text"])
        self._ver_lbl.pack(anchor="w", pady=(14, 2))

        tk.Label(body, text=_("about_repo_hint"), font=F["small"],
                 bg=C["bg"], fg=C["sub"]).pack(anchor="w")

        row = tk.Frame(body, bg=C["bg"])
        row.pack(fill="x", pady=(12, 4))
        self._check_btn = tk.Button(
            row, text=_("about_check_update"), font=F["btn"],
            bg=C["acc"], fg="white", bd=0, padx=16, pady=8,
            cursor="hand2", command=self.start_check,
            activebackground=C["acc"], activeforeground="white")
        self._check_btn.pack(side="left")

        self._open_btn = tk.Button(
            row, text=_("about_open_releases"), font=F["btn"],
            bg=C["panel"], fg=C["text"], bd=0, padx=16, pady=8,
            cursor="hand2",
            command=lambda: webbrowser.open(RELEASES_PAGE))
        self._open_btn.pack(side="left", padx=(10, 0))

        # update status area
        self._status_lbl = tk.Label(body, text="", font=F["body"],
                                    bg=C["bg"], fg=C["sub"],
                                    wraplength=500, justify="left",
                                    anchor="w")
        self._status_lbl.pack(fill="x", pady=(10, 0))

        self._notes_btn = tk.Button(
            body, text=_("about_view_notes"), font=F["small"],
            bg=C["panel"], fg=C["text"], bd=0, padx=10, pady=4,
            cursor="hand2", command=self._open_notes)
        # packed only in UPDATE_AVAILABLE state

        self._progress = ttk.Progressbar(body, maximum=100, length=500)
        self._cancel_btn = tk.Button(
            body, text=_("about_cancel_download"), font=F["small"],
            bg=C["panel"], fg=C["sub"], bd=0, padx=10, pady=4,
            cursor="hand2", command=self._cancel_download)

        # action row
        act = tk.Frame(body, bg=C["bg"])
        act.pack(fill="x", side="bottom", pady=(0, 14))
        self._install_btn = tk.Button(
            act, text=_("about_download_install"), font=F["btn"],
            bg=C["ok"], fg="#0a1a0a", bd=0, padx=18, pady=9,
            cursor="hand2", state="disabled",
            command=self._begin_install)
        self._install_btn.pack(side="right")

    def _fill_version(self):
        cur = get_current_version()
        self._ver_lbl.config(text=f"{_('about_version_label')}  v{cur}")

    # ── state machine → widgets ──────────────────────────────
    def _transition(self, new_state: UpdateState) -> None:
        self._flow.transition(new_state)
        self._apply_ui()

    def _apply_ui(self):
        """Single place mapping the flow state onto widgets."""
        state = self._flow.state
        busy = state in (UpdateState.CHECKING, UpdateState.DOWNLOADING,
                         UpdateState.VERIFYING)
        self._check_btn.config(
            state="disabled" if busy else "normal")
        self._install_btn.config(
            state="normal" if state in (UpdateState.UPDATE_AVAILABLE,
                                        UpdateState.READY_TO_INSTALL)
            else "disabled",
            text=_("about_install_ready")
            if state is UpdateState.READY_TO_INSTALL
            else _("about_download_install"))

        if state is UpdateState.DOWNLOADING:
            self._progress.pack_forget()
            self._progress.pack(fill="x", pady=(4, 2))
            self._cancel_btn.pack(anchor="e")
        else:
            self._progress.pack_forget()
            self._cancel_btn.pack_forget()

        if state is UpdateState.UPDATE_AVAILABLE:
            self._notes_btn.pack(anchor="w", pady=(6, 0))
        else:
            self._notes_btn.pack_forget()

    def _set_status(self, text: str, color: str):
        self._status_lbl.config(text=text, fg=color)

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    # ── check ────────────────────────────────────────────────
    def start_check(self):
        if self._flow.state in (UpdateState.CHECKING, UpdateState.DOWNLOADING,
                                UpdateState.VERIFYING):
            return
        self._token = None      # a stale cancelled token must not poison the check
        self._transition(UpdateState.CHECKING)
        self._set_status(_("about_checking"), C["sub"])
        threading.Thread(target=self._check_worker, daemon=True,
                         name="update-check").start()

    def _check_worker(self):
        try:
            manifest = self._fetch()
        except GenerationCancelled:
            self.root.after(0, lambda: self._check_failed(
                UpdateErrorCode.CANCELLED, ""))
            return
        except UpdateError as exc:
            self.root.after(0, lambda e=exc: self._check_failed(e.code, e.detail))
            return
        except Exception as exc:  # unexpected — still a failed check
            append_update_log(f"unexpected check error: {type(exc).__name__}: {exc}")
            self.root.after(0, lambda e=exc: self._check_failed(
                UpdateErrorCode.NETWORK_ERROR, f"{type(e).__name__}"))
            return
        self.root.after(0, lambda: self._check_done(manifest))

    def _fetch(self):
        from services.updater.manifest import fetch_manifest
        return fetch_manifest(get_current_version(), token=self._token)

    def _check_failed(self, code: UpdateErrorCode, detail: str):
        if not self._alive():
            return
        append_update_log(f"check failed: {code.value} {detail}")
        if self._flow.state is UpdateState.CHECKING:
            self._transition(UpdateState.FAILED)
        msg = _("about_check_failed", err=_err_text(code))
        if code is not UpdateErrorCode.CANCELLED:
            msg += "\n" + _("about_check_failed_hint")
        self._set_status(msg, C["hl"] if code is not UpdateErrorCode.CANCELLED
                         else C["sub"])
        self._apply_ui()

    def _check_done(self, manifest):
        if not self._alive():
            return
        if self._flow.state is not UpdateState.CHECKING:
            return  # dialog closed / cancelled meanwhile
        if manifest is None:
            self._transition(UpdateState.NO_UPDATE)
            self._set_status(
                _("about_up_to_date", version=get_current_version()), C["ok"])
            return
        self._manifest = manifest
        self._transition(UpdateState.UPDATE_AVAILABLE)
        current = get_current_version()
        size_mb = manifest.installer.size / 1048576
        text = _("about_new_found", tag=manifest.tag, current=current)
        if manifest.published_at:
            text += ("\n" + _("about_released_at",
                              date=manifest.published_at[:10]))
        text += "\n" + _("about_size_line", size=f"{size_mb:.0f}")
        self._set_status(text, C["warn"])

    def _open_notes(self):
        if self._manifest is not None:
            webbrowser.open(self._manifest.release_url)

    # ── download ─────────────────────────────────────────────
    def _begin_download(self):
        if self._manifest is None:
            return
        self._token = CancellationToken()
        self._transition(UpdateState.DOWNLOADING)
        self._set_status(_("about_downloading", tag=self._manifest.tag,
                           pct=0, done="0.0", total="?", speed="0.0"), C["sub"])

        def _worker():
            try:
                path = _downloader.download_verified(
                    self._manifest.installer,
                    _state.download_dir(self._manifest.version),
                    token=self._token, progress=self._progress_cb)
            except GenerationCancelled:
                self.root.after(0, lambda: self._download_failed(
                    UpdateErrorCode.CANCELLED, ""))
                return
            except UpdateError as exc:
                self.root.after(0, lambda e=exc: self._download_failed(
                    e.code, e.detail))
                return
            except Exception as exc:
                append_update_log(
                    f"unexpected download error: {type(exc).__name__}: {exc}")
                self.root.after(0, lambda e=exc: self._download_failed(
                    UpdateErrorCode.DOWNLOAD_FAILED, type(e).__name__))
                return
            self.root.after(0, lambda: self._download_done(path))

        threading.Thread(target=_worker, daemon=True,
                         name="update-download").start()

    def _progress_cb(self, stage: str, done: int, total: int, speed: float):
        def _apply():
            if not self._alive():
                return
            if self._flow.state not in (UpdateState.DOWNLOADING,
                                        UpdateState.VERIFYING):
                return
            if stage == "verify":
                if self._flow.state is UpdateState.DOWNLOADING:
                    self._transition(UpdateState.VERIFYING)
                self._set_status(_("about_verifying"), C["sub"])
                if total:
                    self._progress.config(
                        value=min(100, done * 100 // max(1, total)))
                return
            if total:
                pct = done * 100 // total
                self._set_status(
                    _("about_downloading", tag=self._manifest.tag, pct=pct,
                      done=f"{done / 1048576:.1f}",
                      total=f"{total / 1048576:.1f}",
                      speed=f"{speed / 1048576:.1f}"), C["sub"])
                self._progress.config(value=pct)
            else:
                self._set_status(
                    _("about_downloading_nolen",
                      done=f"{done / 1048576:.1f}"), C["sub"])
        self.root.after(0, _apply)

    def _download_done(self, path):
        if not self._alive():
            return
        self._package_path = Path(path)
        if self._flow.state is UpdateState.DOWNLOADING:
            self._transition(UpdateState.VERIFYING)
        self._transition(UpdateState.READY_TO_INSTALL)
        self._set_status(
            _("about_ready", path=str(self._package_path)), C["ok"])

    def _download_failed(self, code: UpdateErrorCode, detail: str):
        if not self._alive():
            return
        append_update_log(f"download failed: {code.value} {detail}")
        was_cancelled = code is UpdateErrorCode.CANCELLED
        if self._flow.state in (UpdateState.DOWNLOADING,
                                UpdateState.VERIFYING):
            self._transition(UpdateState.FAILED)
            self._transition(UpdateState.UPDATE_AVAILABLE
                             if self._manifest is not None else UpdateState.IDLE)
        if was_cancelled:
            self._set_status(_("about_download_cancelled"), C["sub"])
        else:
            self._set_status(
                _("about_install_failed") + "\n" + _err_text(code), C["hl"])
            self.app._log(f"[update] download failed: {code.value} {detail}")
        self._apply_ui()

    def _cancel_download(self):
        if self._token is not None:
            self._token.cancel()

    # ── install ──────────────────────────────────────────────
    def _begin_install(self):
        if self._flow.state is UpdateState.UPDATE_AVAILABLE:
            self._begin_download()
            return
        if self._flow.state is not UpdateState.READY_TO_INSTALL:
            return
        if self._package_path is None or self._manifest is None:
            return
        if not getattr(sys, "frozen", False):
            # dev environment: no in-app install
            messagebox.showinfo(
                _("about_title"), _("about_dev_hint"), parent=self)
            webbrowser.open(RELEASES_PAGE)
            return
        if _installer.detect_install_mode():
            self._installer_install()
        else:
            self._portable_install()

    def _installer_install(self):
        # §18: never force-exit over running generation/queue tasks
        if self.app._has_active_tasks():
            choice = messagebox.askyesnocancel(
                _("about_tasks_running_title"),
                _("about_tasks_running_body"), parent=self)
            if choice is not True:
                self._set_status(_("about_tasks_wait_hint"), C["sub"])
                return
        if not messagebox.askyesno(
                _("about_title"), _("about_confirm_install_body"),
                parent=self):
            return

        install_dir = _installer.detect_install_dir()
        updater_exe = Path(sys.executable).parent / "2image_updater.exe"
        try:
            if updater_exe.is_file():
                args = [
                    "--installer", str(self._package_path),
                    "--expected-sha256", self._manifest.installer.sha256,
                    "--install-dir", str(install_dir),
                    "--parent-pid", str(os.getpid()),
                    "--parent-exe", sys.executable,
                    "--from-version", get_current_version(),
                    "--target-version", self._manifest.version,
                ]
                _installer.launch_detached(updater_exe, args)
            else:
                # degraded path: no bundled updater → direct silent install
                # (no re-verification / rollback protection)
                messagebox.showwarning(
                    _("about_title"), _("about_updater_missing"), parent=self)
                append_update_log(
                    "2image_updater.exe missing — falling back to direct "
                    "silent install")
                cmd = _installer.build_installer_command(
                    self._package_path, install_dir,
                    _state.log_path().with_name("update-install.log"))
                subprocess.Popen(
                    cmd, close_fds=True,
                    creationflags=subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP)
        except OSError as exc:
            append_update_log(f"installer launch failed: {exc}")
            self._fail_install(str(exc))
            return

        self._transition(UpdateState.WAITING_APP_EXIT)
        self._transition(UpdateState.INSTALLING)
        self._set_status(_("about_installing"), C["ok"])
        # hand control to the updater: exit normally so it can take over
        self.root.after(400, self.app.root.destroy)

    def _portable_install(self):
        # §20 phase 1: run the installer or send the user to releases
        if messagebox.askyesno(
                _("about_title"),
                _("about_portable_ready_body", path=str(self._package_path)),
                parent=self):
            try:
                _installer.launch_detached(self._package_path)
            except OSError as exc:
                self._fail_install(str(exc))
                return
            self._set_status(_("about_portable_launched"), C["ok"])
        else:
            webbrowser.open(self._manifest.release_url)

    def _fail_install(self, detail: str):
        # reachable from READY / WAITING_APP_EXIT / INSTALLING; land on
        # UPDATE_AVAILABLE so the user can retry (package is reused)
        if self._flow.state is not UpdateState.FAILED:
            self._transition(UpdateState.FAILED)
        if self._manifest is not None:
            self._transition(UpdateState.UPDATE_AVAILABLE)
        self._set_status(_("about_install_failed") + "\n" + detail, C["hl"])

    # ── lifecycle ────────────────────────────────────────────
    def _on_close(self):
        if self._token is not None:
            self._token.cancel()
        if (self._flow.state is UpdateState.UPDATE_AVAILABLE
                and self._manifest is not None):
            _state.dismiss(self._manifest.version)
        self.destroy()
