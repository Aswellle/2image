"""Pytest configuration and fixtures."""
import time

import pytest
import tkinter as tk

# Tcl resolves its script library per interpreter; on the Windows CI runner that
# search intermittently fails with `TclError: invalid command name
# "tcl_findLibrary"` and succeeds on the next attempt. Retry before giving up so
# a transient bootstrap failure skips instead of failing the suite.
_TK_ATTEMPTS = 3
_TK_RETRY_DELAY = 0.3


def _make_tk_root():
    """Create a withdrawn Tk root, or None when tcl/tk is unavailable."""
    last_error = None
    for attempt in range(_TK_ATTEMPTS):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            last_error = exc
            if attempt < _TK_ATTEMPTS - 1:
                time.sleep(_TK_RETRY_DELAY * (attempt + 1))
            continue
        except Exception as exc:  # non-Tcl runtime errors are not retryable
            last_error = exc
            break
        root.withdraw()
        return root
    if last_error is not None:
        print(f"tkinter root unavailable: {last_error!r}")
    return None


def _tkinter_available() -> bool:
    """Check if tcl/tk runtime is available (CI environments may not have it)."""
    root = _make_tk_root()
    if root is None:
        return False
    try:
        root.destroy()
    except tk.TclError:
        pass
    return True


# Skip marker for tests requiring a display/tcl runtime
skip_if_no_tk = pytest.mark.skipif(
    not _tkinter_available(),
    reason="tcl/tk runtime not available in this environment (headless CI)",
)




@pytest.fixture(scope="session")
def tk_session_root():
    """整个 pytest 会话共享一个 Tk root。

    Windows 上反复创建/销毁 Tk 解释器会触发 Tcl C 层崩溃
    （fatal 0x80000003 / access violation，见 CI test_thumbnail 处），
    因此测试统一复用同一个解释器；测试自身只创建/销毁自己的
    Frame / Toplevel，绝不 destroy 这个 root。
    """
    root = _make_tk_root()
    if root is None:
        pytest.skip("tcl/tk runtime not available (headless CI)")
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


@pytest.fixture
def tk_root(tk_session_root):
    """共享 Tk root（函数级别名；勿在测试中 destroy）。"""
    return tk_session_root



@pytest.fixture
def in_memory_db():
    """Switch repository to in-memory SQLite."""
    from data import repository
    repository._set_test_db(":memory:")
    repository.init_db()
    yield
    # Cleanup handled by SQLite in-memory auto-drop


@pytest.fixture
def mock_app():
    """Minimal mock AppProtocol for sidebar/main_content tests."""
    class MockApp:
        def __init__(self):
            self.root = None  # set later
            self.cfg = {}
            self.sel_id = None
            self.cur_path = None
            self._cur_bytes = None
            self._sidebar_w = 320
            self.MAX_NICK_LEN = 20
            self._log_calls = []
            self._st_calls = []
        def _log(self, msg): self._log_calls.append(msg)
        def _st(self, msg, k="ok"): self._st_calls.append((msg, k))
        def _toast(self, msg, level="info"): self._st_calls.append((msg, level))
        def _refresh_hist(self, load_all=False, keep_scroll=False): pass
        def _refresh_tag_stats(self): pass
        def _load_entry(self, e): pass
        def _gen(self, event=None): pass
        def _reset_view(self): pass
        def _export(self): pass
        def _open_viewer(self): pass
        def _set_cmp_from_entry(self, e): pass
        def _display_title(self, e):
            return e.get("nickname") or e.get("prompt", "")[:20]
    return MockApp()


@pytest.fixture(autouse=True)
def isolate_real_config(tmp_path, monkeypatch):
    """安全网：任何测试的磁盘写入都重定向到临时目录。

    覆盖在 import 期绑定路径的模块全局（from-import 场景无法通过
    patch settings 本身生效）：
      - config.settings.CONFIG_FILE / APP_DIR（save_config 运行时读取）
      - data.repository.DB_FILE（SQLite 历史库）
      - services.logger.LOG_FILE（调试日志）
      - data.file_ownership.IMAGES_DIR（受管图片目录）
      - services.phrase_library._CUSTOM_FILE（自定义短语词库）
      - services.generation.budget.SPEND_FILE（付费消耗台账）

    事故背景：2026-10-04 测试曾覆写真实 ~/2image/config.json 导致
    用户配置丢失；DB/日志/词库路径此前同样未被护栏覆盖。
    """
    import config.settings as _settings
    monkeypatch.setattr(_settings, "CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(_settings, "APP_DIR", str(tmp_path))

    import data.repository as _repo
    monkeypatch.setattr(_repo, "DB_FILE", str(tmp_path / "history.db"))

    import services.logger as _logger
    monkeypatch.setattr(_logger, "LOG_FILE", str(tmp_path / "debug.log"))

    import data.file_ownership as _ownership
    monkeypatch.setattr(_ownership, "IMAGES_DIR", str(tmp_path / "images"))

    import services.phrase_library as _phrases
    monkeypatch.setattr(_phrases, "_CUSTOM_FILE",
                        str(tmp_path / "phrase_library.json"))

    import services.generation.budget as _budget
    monkeypatch.setattr(_budget, "SPEND_FILE", str(tmp_path / "spend.json"))


@pytest.fixture
def app(tk_root, monkeypatch):
    """构造完整 App（内存库 + mock 配置读写），yield (app, saved_cfg)。"""
    import data.repository as repo
    from config.fonts import init_fonts
    from config.settings import DEFAULT_CONFIG
    import ui.app as app_mod

    repo._set_test_db(":memory:")
    repo.init_db()
    init_fonts()
    cfg = dict(DEFAULT_CONFIG)
    cfg["show_wizard_on_start"] = False
    cfg["sidebar_width"] = 999          # 超上限，应被钳制到 SIDEBAR_MAX
    saved = {}
    monkeypatch.setattr(app_mod, "load_config", lambda: dict(cfg))
    monkeypatch.setattr(app_mod, "save_config",
                        lambda c: saved.update(dict(c)))
    # 共享会话 root 上以 Toplevel 承载 App，避免销毁整个解释器
    top = tk.Toplevel(tk_root)
    top.withdraw()
    a = app_mod.App(top)
    tk_root.update()
    yield a, saved
    try:
        top.destroy()   # 触发侧栏 <Destroy> 钩子 → loader shutdown
    except tk.TclError:
        pass
