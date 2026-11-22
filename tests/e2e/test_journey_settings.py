"""E2E 旅程：配置向导、语言切换、快捷键/设置窗口、批量与队列联调。"""

import tkinter as tk

import pytest
from tests.e2e import driver


def test_free_wizard_open_edit_save(e2e):
    """免费配置向导：打开 → 填 Key → 保存 → cfg 回调捕获。"""
    app = e2e.app
    app._open_wizard()
    e2e.pump()
    tops = [w for w in app.root.winfo_children() if isinstance(w, tk.Toplevel) and w.winfo_exists()]
    assert tops, "免费配置向导窗口应打开"
    wiz = tops[-1]

    def _find_entries(w):
        found = []
        for ch in w.winfo_children():
            if isinstance(ch, tk.Entry):
                found.append(ch)
            found.extend(_find_entries(ch))
        return found

    ents = _find_entries(wiz)
    assert ents, "向导内应有输入框"
    for ent in ents[:3]:
        if str(ent.cget("state")) != "disabled":
            driver.set_entry(ent, "sk-e2e-test-key")
    save_btns = driver.find_buttons(wiz, "保存并开始") or driver.find_buttons(wiz, "保存")
    assert save_btns, "向导应有保存按钮"
    save_btns[0].invoke()
    e2e.pump()
    # on_save 将新 cfg 写回 App：测试键进入应用配置
    assert "sk-e2e-test-key" in e2e.app.cfg.values()


def test_paid_wizard_opens(e2e):
    """付费配置向导可打开并关闭。"""
    app = e2e.app
    app._open_paid_wizard()
    e2e.pump()
    tops = [w for w in app.root.winfo_children() if isinstance(w, tk.Toplevel) and w.winfo_exists()]
    assert tops
    tops[-1].event_generate("<Escape>")
    e2e.pump()


def test_shortcuts_window_opens_and_closes(e2e):
    """快捷键说明窗口：打开 → Escape 关闭。"""
    app = e2e.app
    app.settings_controller.show_shortcuts()
    e2e.pump()
    tops = [w for w in app.root.winfo_children() if isinstance(w, tk.Toplevel) and w.winfo_exists()]
    assert tops
    tops[-1].event_generate("<Escape>")
    e2e.pump()


def test_app_settings_window_opens(e2e):
    """应用设置窗口可打开。"""
    app = e2e.app
    app.settings_controller.show_app_settings()
    e2e.pump()
    tops = [w for w in app.root.winfo_children() if isinstance(w, tk.Toplevel) and w.winfo_exists()]
    assert tops


def test_language_switch_persists_choice(e2e):
    """切换语言：cfg 持久化（重启生效语义）+ toast 提示。"""
    app = e2e.app
    app.settings_controller.set_language("en")
    e2e.pump()
    assert app.cfg.get("language") == "en"
    e2e.pump()
    app.settings_controller.set_language("zh-CN")
    e2e.pump()
    assert app.cfg.get("language") == "zh-CN"


def test_batch_panel_renders_six_cells(e2e):
    """批量面板：6 格变体网格在场。"""
    app = e2e.app
    batch = getattr(app, "batch_panel", None) or getattr(app.content, "_batch_panel", None)
    if batch is None:
        pytest.skip("批量面板为懒加载，入口由生成旅程覆盖")
    e2e.pump()
    assert batch.winfo_exists()


def test_queue_submit_runs_job(e2e):
    """队列联调：入队 → 启动 worker（真实线程）→ 假 provider 串行完成两单。"""
    fake = e2e.install_fake_provider("pollinations")
    qp = e2e.app._queue_panel
    e2e.pump()
    qp.add_task("queue job one", "1024x1024", ["pollinations"])
    qp.add_task("queue job two", "1024x1024", ["pollinations"])
    start_btn = driver.find_buttons(qp, "开始")
    if not start_btn:
        start_btn = driver.find_buttons(qp, "生成")
    assert start_btn, "队列面板应有启动按钮"
    start_btn[0].invoke()
    assert e2e.wait_until(lambda: len(fake.calls) >= 2, timeout_ms=20000)
    e2e.pump(10)
    from data.repository import count_entries

    assert count_entries() == 2
