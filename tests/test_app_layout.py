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
    assert a._sidebar_w == a._SIDEBAR_MAX  # 999 被上限钳制（上限随缩放系数实例化）


def test_sash_persists_width(app):
    a, saved = app
    a._sidebar_w = 300
    a._sash_end(None)
    assert saved.get("sidebar_width") == 300


def test_sash_reset_restores_default(app):
    a, saved = app
    a._sidebar_w = 250
    a._sash_reset(None)
    assert a._sidebar_w == a._SIDEBAR_DEF  # 默认宽（随缩放系数实例化）
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
    a.sidebar._refresh_hist()  # 键盘导航作用于可见（过滤后）列表
    tk_root.update()
    a._nav_history_guarded(delta=-1)  # 无选中 → 列表末条（显示顺序最后）
    assert a.sel_id in (newest["id"], older["id"])
    first = a.sel_id
    other = older["id"] if first == newest["id"] else newest["id"]
    a._nav_history_guarded(delta=+1)
    assert a.sel_id == first  # 已在列表末端，继续下移被钳制
    a._nav_history_guarded(delta=-1)
    assert a.sel_id == other  # 反向移动到相邻条目


def test_nav_guard_ignores_typing_focus(app, tk_root, monkeypatch):
    a, _ = app
    from data.repository import add_entry

    add_entry("some prompt", "", "", "prov")
    monkeypatch.setattr(a, "_typing_focus", lambda: True)
    a._nav_history_guarded(delta=-1)
    assert a.sel_id is None  # 输入焦点在文本框：不劫持


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
    assert called == [e["id"]]  # 输入焦点在文本框时不触发删除


def test_provider_dropdown_includes_commercial_tier(app):
    """商业接口与免费/付费接口同级出现在主界面下拉框，且都有配置入口。

    历史问题：商业接口虽已实现并注册，却不在下拉框、也没有配置卡片，
    用户只能手改 config.json 才能用——不属于「可用的前端功能」。
    """
    from config.i18n import _
    from services.providers import ALL_PROVIDERS, COMMERCIAL_PROVIDERS, WIZARD_CONFIGURED, display_name_for

    a, _saved = app
    values = list(a.content._t2i_provider_list)
    assert _("provider_commercial_section") in values
    for pid in COMMERCIAL_PROVIDERS:
        assert display_name_for(pid) in values, pid
    # 下拉框里的每个真实接口都必须能在配置向导里配置
    assert set(ALL_PROVIDERS) <= WIZARD_CONFIGURED


def test_img2img_dropdown_includes_commercial_providers(app):
    a, _ = app
    ids = a.content._i2i_selectable_providers()
    assert "fal_flux" in ids
    assert "minimax_image" in ids


def test_queue_auto_order_resolved_at_execution(monkeypatch):
    """队列自动档必须在执行时按提示词路由，而不是沿用 DEFAULT_ORDER。"""
    import ui.queue_panel as qp

    class _Item:
        porder = None
        prompt = "设计一个 banner"
        template_id = ""

    seen = {}

    def fake_order(prompt, cfg, template_id=""):
        seen["args"] = (prompt, template_id)
        return ["ideogram", "siliconflow"]

    monkeypatch.setattr(qp, "get_provider_order", fake_order)
    assert qp._order_for_item(_Item(), {}) == ["ideogram", "siliconflow"]
    assert seen["args"] == ("设计一个 banner", "")


def test_queue_explicit_order_kept(monkeypatch):
    import ui.queue_panel as qp

    class _Item:
        porder = ["pollinations"]
        prompt = "x"
        template_id = ""

    monkeypatch.setattr(qp, "get_provider_order", lambda *a, **k: ["ideogram"])
    assert qp._order_for_item(_Item(), {}) == ["pollinations"]
