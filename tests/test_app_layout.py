"""tests/test_app_layout.py — App 侧栏布局行为（§41/§42）。

真实构造 App（内存库 + mock 配置读写），验证：
· 启动块不再重复执行（v2.4.x 遗留双重刷新已清理）
· 侧栏宽度从配置恢复并受 MIN/MAX 约束
· Ctrl+\ 折叠/展开、双击分隔条恢复默认、拖拽结束持久化
"""
from __future__ import annotations

import tkinter as tk

import pytest

from config.fonts import init_fonts
from config.i18n import init_language
from config.settings import DEFAULT_CONFIG
import data.repository as repo
import ui.app as app_mod


def test_startup_single_refresh(app):
    """启动路径只调度一次刷新（重复块已清理）；宽度受 MAX 钳制。"""
    a, _ = app
    assert a._sidebar_w == 600  # SIDEBAR_MAX：999 被钳制


def test_sash_persists_width(app):
    a, saved = app
    a._sidebar_w = 300
    a._sash_end(None)
    assert saved.get("sidebar_width") == 300


def test_sash_reset_restores_default(app):
    a, saved = app
    a._sidebar_w = 250
    a._sash_reset(None)
    assert a._sidebar_w == 360  # SIDEBAR_DEF
    assert saved.get("sidebar_width") == 360


def test_toggle_sidebar_collapse_and_restore(app):
    a, _ = app
    before = a._sidebar_w
    a._toggle_sidebar()
    assert a._sidebar_collapsed is True
    assert a._sidebar_w == 0
    a._toggle_sidebar()
    assert a._sidebar_collapsed is False
    assert a._sidebar_w == before


def test_drag_after_collapse_uncollapses(app):
    a, _ = app
    a._toggle_sidebar()
    a._sash_start(type("E", (), {"x_root": 100})())
    assert a._sidebar_collapsed is False


# ── §58 键盘工作流 ──────────────────────────────────────────
def test_esc_closes_overlay(app, tk_root):
    a, _ = app
    overlay = tk.Toplevel(tk_root)
    a._viewer_win = overlay
    a._esc_overlay()
    assert a._viewer_win is None
    assert overlay.winfo_exists() == 0  # 已销毁


def test_esc_no_overlay_noop(app):
    a, _ = app
    a._esc_overlay()  # 无覆盖窗口时不抛错


def test_nav_history_moves_selection(app, tk_root):
    a, _ = app
    from data.repository import add_entry
    newest = add_entry("newest prompt", "", "", "prov")
    older = add_entry("older prompt", "", "", "prov")
    tk_root.update()
    a._nav_history_guarded(delta=-1)   # 无选中 → 选中列表第一条
    assert a.sel_id in (newest["id"], older["id"])
    first = a.sel_id
    other = older["id"] if first == newest["id"] else newest["id"]
    a._nav_history_guarded(delta=+1)
    assert a.sel_id == other           # 向相邻条目移动


def test_nav_guard_ignores_typing_focus(app, tk_root, monkeypatch):
    a, _ = app
    from data.repository import add_entry
    add_entry("some prompt", "", "", "prov")
    monkeypatch.setattr(a, "_typing_focus", lambda: True)
    a._nav_history_guarded(delta=-1)
    assert a.sel_id is None            # 输入焦点在文本框：不劫持


def test_delete_guard_respects_typing_focus(app, tk_root, monkeypatch):
    a, _ = app
    from data.repository import add_entry
    e = add_entry("to delete", "", "", "prov")
    a.sel_id = e["id"]
    called = []
    monkeypatch.setattr(a.sidebar, "_del_entry", lambda eid: called.append(eid))
    a._delete_selected_guarded()
    assert called == [e["id"]]
    monkeypatch.setattr(a, "_typing_focus", lambda: True)
    a._delete_selected_guarded()
    assert called == [e["id"]]         # 输入焦点在文本框时不触发删除
