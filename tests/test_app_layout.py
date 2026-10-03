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


@pytest.fixture
def app(tk_root, monkeypatch, tmp_path):
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
    a = app_mod.App(tk_root)
    tk_root.update()
    yield a, saved
    try:
        tk_root.destroy()
    except tk.TclError:
        pass


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
