"""统计看板单例语义回归测试。

历史缺陷：StatsDashboard 是普通类、内部 Toplevel 为局部变量，
App._show_stats 的懒单例判断对其调用 winfo_exists/lift 直接 AttributeError，
导致二次打开静默失败、看板内刷新按钮（销毁后重建路径）崩溃。
"""

import tkinter as tk


def _open(app):
    real, _ = app
    real._show_stats()
    return real, real._stats_win


def test_stats_dashboard_reopen_without_error(app):
    real, dash = _open(app)
    assert dash is not None
    assert dash.winfo_exists()

    # 模拟用户关闭窗口后再次打开 —— 不得抛 AttributeError
    dash.win.destroy()
    real._show_stats()
    assert real._stats_win.winfo_exists()
    real._stats_win.win.destroy()
    real._stats_win = None


def test_stats_dashboard_refresh_recreates_window(app):
    real, dash = _open(app)
    dash.win.destroy()

    real._show_stats()
    second = real._stats_win
    assert second is not dash
    assert second.winfo_exists()
    second.win.destroy()
    real._stats_win = None


def test_stats_dashboard_lift_and_focus_delegate(app):
    real, dash = _open(app)
    # 单例 else 分支调用的两个方法必须真实存在且可用
    dash.lift()
    dash.focus_force()
    assert isinstance(dash.win, tk.Toplevel)
    dash.win.destroy()
    real._stats_win = None
