"""tests/test_sidebar_ux.py — 侧栏滚动/筛选 UX 回归（UIUX P0-06/07/08、§44）。

真实构造 HistorySidebar（mock_app + 内存库），验证：
· 滚动事件归一化（高精度小步长累积）
· 搜索清除按钮与筛选状态条显隐
· keep_scroll 刷新不抛错
"""
from __future__ import annotations

import tkinter as tk

import pytest

from config.fonts import init_fonts
from ui.sidebar import HistorySidebar


class _FakeWheelEvent:
    def __init__(self, delta):
        self.delta = delta
        self.num = None


@pytest.fixture
def sidebar(tk_root, mock_app, in_memory_db):
    init_fonts()
    mock_app.root = tk_root
    frame = tk.Frame(tk_root)
    frame.pack()
    sb = HistorySidebar(frame, mock_app)
    tk_root.update()
    yield sb
    try:
        frame.destroy()
    except tk.TclError:
        pass


def test_sidebar_constructs(sidebar):
    assert sidebar.hc.winfo_exists()
    assert sidebar.sv.get() == ""


def test_wheel_accumulates_small_deltas(sidebar):
    """高精度滚轮 delta=40 → 三次累积为一整行，残余归零。"""
    for _ in range(3):
        sidebar._on_wheel(_FakeWheelEvent(40))
    assert sidebar._wheel_acc == pytest.approx(0.0)


def test_wheel_standard_delta_one_unit(sidebar):
    sidebar._on_wheel(_FakeWheelEvent(-120))
    assert sidebar._wheel_acc == pytest.approx(0.0)


def test_btn45_scrolls(sidebar):
    e = _FakeWheelEvent(0)
    e.num = 4
    sidebar._on_btn45(e)  # 不应抛错
    e.num = 5
    sidebar._on_btn45(e)


def test_filter_status_hidden_by_default(sidebar):
    with pytest.raises(tk.TclError):
        sidebar._filter_status.pack_info()  # 未 pack = 隐藏


def test_filter_status_shows_on_fav(sidebar, tk_root):
    sidebar._filter_fav()
    sidebar._filter_status.pack_info()  # 已 pack = 可见
    assert sidebar._fav_only is True


def test_clear_filters_resets_state(sidebar, tk_root):
    sidebar._filter_fav()
    sidebar._clear_search()
    sidebar._clear_filters()
    assert sidebar._fav_only is False
    assert sidebar._tag_filter == ""
    with pytest.raises(tk.TclError):
        sidebar._filter_status.pack_info()


def test_clear_search_empties_var(sidebar):
    sidebar.sv.set("robot")
    sidebar._clear_search()
    assert sidebar.sv.get() == ""


def test_refresh_hist_keep_scroll_runs(sidebar, tk_root, in_memory_db):
    from data.repository import add_entry
    add_entry("a test prompt", "", "", "prov")
    tk_root.update()
    sidebar._refresh_hist(keep_scroll=True)
    tk_root.update()
    assert sidebar.hc.winfo_exists()
    sidebar._refresh_hist()
    tk_root.update()


def test_refresh_hist_preserves_yview(sidebar, tk_root, in_memory_db):
    """有内容时 keep_scroll=True 不重置滚动位置。"""
    from data.repository import add_entry
    for i in range(30):
        add_entry(f"prompt {i} " + "x" * 60, "", "", "prov")
    tk_root.update()
    sidebar._refresh_hist()
    tk_root.update()
    # 滚到中部再以 keep_scroll 刷新
    sidebar.hc.yview_moveto(0.5)
    sidebar._refresh_hist(keep_scroll=True)
    tk_root.update()
    first, _ = sidebar.hc.yview()
    assert first == pytest.approx(0.5, abs=0.05)
