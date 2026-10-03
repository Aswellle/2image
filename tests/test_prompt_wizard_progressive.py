"""tests/test_prompt_wizard_progressive.py — P1-25 渐进披露回归。"""
from __future__ import annotations

import tkinter as tk

import pytest

from config.fonts import init_fonts
from config.i18n import init_language
from config.settings import DEFAULT_CONFIG


@pytest.fixture
def wizard(tk_root, mock_app):
    init_fonts()
    init_language(DEFAULT_CONFIG)
    mock_app.root = tk_root
    mock_app.cfg = dict(DEFAULT_CONFIG)
    from ui.prompt_wizard import PromptWizard
    w = PromptWizard(mock_app)
    tk_root.update()
    yield w
    try:
        w.destroy()
    except tk.TclError:
        pass


def test_advanced_dims_built_but_collapsed(wizard):
    """7 个维度对象全部存在；高级 5 维默认收起。"""
    for attr in ("_dim_style", "_dim_mood", "_dim_detail", "_dim_comp",
                 "_dim_light", "_dim_cam", "_dim_qual"):
        assert getattr(wizard, attr) is not None
    with pytest.raises(tk.TclError):
        wizard._adv_host.pack_info()          # 未 pack = 收起
    assert wizard._adv_open is False


def test_toggle_expands_and_collapses(wizard, tk_root):
    wizard._toggle_advanced_dims()
    tk_root.update()
    assert wizard._adv_open is True
    wizard._adv_host.pack_info()              # 已 pack = 展开
    assert "▾" in wizard._adv_toggle.cget("text")

    wizard._toggle_advanced_dims()
    tk_root.update()
    assert wizard._adv_open is False
    with pytest.raises(tk.TclError):
        wizard._adv_host.pack_info()
    assert "▸" in wizard._adv_toggle.cget("text")


def test_collapse_keeps_dim_values(wizard):
    """收起不影响已选维度值 —— 参数逻辑与可见性解耦。"""
    wizard._dim_style.var.set(wizard._dim_style._presets[1])
    wizard._toggle_advanced_dims()  # 收起（若已展开）不影响取值
    assert wizard._dim_style.var.get() == wizard._dim_style._presets[1]
