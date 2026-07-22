from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

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


def test_main_keeps_root_hidden_until_app_is_built(monkeypatch):
    root = Mock()
    monkeypatch.setattr(main, "_set_windows_app_user_model_id", Mock())
    monkeypatch.setattr(main, "_enable_dpi_awareness", Mock())
    monkeypatch.setattr(main, "_configure_window_icon", Mock())
    monkeypatch.setattr(main.tk, "Tk", Mock(return_value=root))

    class FakeImage:
        MAX_IMAGE_PIXELS = None

    class FakeApp:
        def __init__(self, received_root):
            assert received_root is root
            root.app_built()

    monkeypatch.setitem(__import__("sys").modules, "PIL", SimpleNamespace(Image=FakeImage))
    monkeypatch.setitem(__import__("sys").modules, "config.fonts", SimpleNamespace(init_fonts=Mock()))
    monkeypatch.setitem(
        __import__("sys").modules,
        "data.repository",
        SimpleNamespace(init_db=Mock(), migrate_from_json=Mock(return_value=0)),
    )
    monkeypatch.setitem(__import__("sys").modules, "config.settings", SimpleNamespace(APP_DIR="."))
    monkeypatch.setitem(__import__("sys").modules, "ui.app", SimpleNamespace(App=FakeApp))

    main.main()

    assert root.method_calls == [
        call.withdraw(),
        call.app_built(),
        call.deiconify(),
        call.mainloop(),
    ]


def test_app_initial_geometry_stays_within_screen(monkeypatch):
    from ui.app import App

    root = Mock()
    root.winfo_screenwidth.return_value = 1280
    root.winfo_screenheight.return_value = 720
    monkeypatch.setattr(App, "_build_menu", Mock())
    monkeypatch.setattr(App, "_build", Mock())
    monkeypatch.setattr(App, "_bind_hotkeys", Mock())
    monkeypatch.setattr(App, "_update_status_bar_tokens", Mock())
    monkeypatch.setattr("ui.app.load_config", lambda: {"show_wizard_on_start": False})
    monkeypatch.setattr("ui.app.init_theme", Mock())
    monkeypatch.setattr("ui.app.init_language", Mock())

    App(root)

    root.title.assert_called_once_with("✨ 文字生图工具 v10")
    root.geometry.assert_called_once_with("1254x684")
    root.minsize.assert_called_once_with(1000, 684)
    root.state.assert_called_once_with("zoomed")
