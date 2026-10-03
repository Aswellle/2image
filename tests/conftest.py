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
