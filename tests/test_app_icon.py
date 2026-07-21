from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import ctypes
import main


def test_resource_path_uses_pyinstaller_bundle(monkeypatch):
    monkeypatch.setattr(main.sys, "_MEIPASS", r"C:\bundle", raising=False)

    assert main._resource_path(main._ICON_FILE) == r"C:\bundle\ICON_256x256.ico"


def test_resource_path_uses_source_directory(monkeypatch):
    monkeypatch.delattr(main.sys, "_MEIPASS", raising=False)

    assert Path(main._resource_path(main._ICON_FILE)) == Path(main.__file__).parent / main._ICON_FILE


def test_set_windows_app_user_model_id(monkeypatch):
    shell32 = Mock()
    monkeypatch.setattr(main.sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(shell32=shell32))

    main._set_windows_app_user_model_id()

    shell32.SetCurrentProcessExplicitAppUserModelID.assert_called_once_with(main._APP_USER_MODEL_ID)


def test_configure_window_icon_uses_packaged_icon(monkeypatch):
    root = Mock()
    monkeypatch.setattr(main, "_resource_path", lambda filename: rf"C:\bundle\{filename}")

    main._configure_window_icon(root)

    root.iconbitmap.assert_called_once_with(r"C:\bundle\ICON_256x256.ico")
