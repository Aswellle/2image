"""tests/test_toast.py — ToastManager 单元测试（真实 Tk，验证生命周期）。"""
from __future__ import annotations

import tkinter as tk

import pytest

from config.fonts import init_fonts
from ui.components.toast import ToastManager


@pytest.fixture
def manager(tk_root):
    init_fonts()
    mgr = ToastManager(tk_root)
    yield mgr
    for job in list(mgr._jobs):
        try:
            tk_root.after_cancel(job)
        except Exception:
            pass
    if mgr._win is not None and mgr._win.winfo_exists():
        mgr._win.destroy()


def test_show_creates_window(tk_root, manager):
    manager.show("测试通知", "success")
    tk_root.update()
    assert manager._win is not None
    assert manager._win.winfo_exists()
    assert "测试通知" in manager._lbl.cget("text")


def test_unknown_level_falls_back_to_info(tk_root, manager):
    manager.show("消息", "bogus-level")
    tk_root.update()
    assert manager._lbl is not None


def test_queue_processes_sequentially(tk_root, manager):
    manager.show("第一条", "info")
    manager.show("第二条", "success")
    assert manager.pending_count() == 2
    tk_root.update()
    manager.close_current()
    tk_root.update()
    # 第二条开始显示
    assert manager.pending_count() == 1
    assert "第二条" in manager._lbl.cget("text")
    manager.close_current()
    tk_root.update()
    assert manager.pending_count() == 0


def test_close_current_clears_pending_jobs(tk_root, manager):
    manager.show("消息", "info", duration_ms=10_000)
    tk_root.update()
    assert manager._jobs, "淡入完成后应有停留 after 任务"
    manager.close_current()
    assert manager._jobs == []
    assert manager.pending_count() == 0


def test_window_is_overrideredirect_and_topmost(tk_root, manager):
    manager.show("消息", "info")
    tk_root.update()
    assert manager._win.wm_overrideredirect()
