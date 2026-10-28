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


def test_loader_threads_shutdown_with_sidebar(tk_root, mock_app, in_memory_db):
    """宿主 Frame 销毁时 ThumbnailLoader 线程全部退出（CI 崩溃回归）。"""
    import time
    init_fonts()
    mock_app.root = tk_root
    frame = tk.Frame(tk_root)
    frame.pack()
    sb = HistorySidebar(frame, mock_app)
    loader = sb._thumb_loader
    tk_root.update()
    frame.destroy()          # <Destroy> 钩子应触发 shutdown
    time.sleep(0.1)
    assert loader._stopped is True
    assert not any(t.is_alive() for t in loader._threads)


def test_empty_search_state_offers_clear_action(sidebar, in_memory_db):
    """搜索无匹配的空态必须给出恢复路径，而非只有一行死文字。"""
    from data.repository import add_entry
    add_entry("a castle", "castle", "x.png", "P")

    sidebar.sv.set("zzz-no-hit")
    sidebar._refresh_hist()
    sidebar.app.root.update()

    texts = []
    for w in sidebar.hi.winfo_children():
        for c in w.winfo_children():
            if isinstance(c, tk.Button):
                texts.append(str(c.cget("text")))
        if isinstance(w, tk.Button):
            texts.append(str(w.cget("text")))
    assert any("清除搜索" in t or "Clear search" in t for t in texts), texts


def test_empty_first_use_state_has_guidance(sidebar):
    """首次使用空态应提示下一步动作，而非仅"暂无记录"。"""
    from config.i18n import _
    sidebar._refresh_hist()
    sidebar.app.root.update()
    def _walk(w):
        for c in w.winfo_children():
            yield c
            yield from _walk(c)

    labels = " ".join(
        str(w.cget("text")) for w in _walk(sidebar.hi) if isinstance(w, tk.Label)
    )
    assert _("empty_first_use_hint") in labels


def test_count_entries_respects_filters(in_memory_db):
    """count_entries 过滤计数与 get_all_entries 同语义。"""
    from data.repository import add_entry, count_entries, get_all_entries, update_tags
    e1 = add_entry("castle on hill", "castle", "x1.png", "P")
    e2 = add_entry("sunset beach", "sunset", "x2.png", "P")
    update_tags(e2["id"], "风景")

    assert count_entries() == 2
    assert count_entries(keyword="castle") == 1
    assert count_entries(tag_filter="风景") == 1
    assert count_entries(only_favorites=True) == 0
    # 与 get_all_entries 的过滤结果交叉验证
    assert len(get_all_entries(keyword="castle")) == count_entries(keyword="castle")
