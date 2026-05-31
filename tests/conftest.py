"""Pytest fixtures for text-to-image tests."""
import pytest
import tkinter as tk


@pytest.fixture
def tk_root():
    """Create a real Tk root for widget tests."""
    root = tk.Tk()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


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
        def _refresh_hist(self, load_all=False): pass
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
