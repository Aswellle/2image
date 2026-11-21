"""tests/test_dropdown_style.py — 全局下拉框视觉的令牌派生护栏。

样式层断言用 ttk style.lookup；弹层 option_add 的值用 spy 捕获
（Tk 的 option get 查询需要真实 Combobox 弹层窗口路径，不可直查）。
主题改令牌时下拉框随之变化，不允许样式脱离令牌体系。
"""

from unittest.mock import patch

import pytest

from tests.conftest import skip_if_no_tk


@skip_if_no_tk
def test_dropdown_style_token_derived(tk_session_root):
    from config.fonts import init_fonts
    from config.theme import DARK_THEME as C
    from tkinter import ttk

    init_fonts()
    from ui.components.dropdown import install_dropdown_style

    install_dropdown_style(tk_session_root)
    style = ttk.Style(tk_session_root)

    # 字段底色与边框来自令牌
    assert style.lookup("TCombobox", "fieldbackground", ("readonly", "!focus")) == C["entry"]
    assert style.lookup("TCombobox", "bordercolor", ("!focus",)) == C["sep"]
    # 获焦绿边：与 Entry 获焦（_gb）同语言
    assert style.lookup("TCombobox", "bordercolor", ("focus",)) == C["ok"]
    # 箭头区 hover 提亮为紫系辅助色（非主色 hl）
    assert style.lookup("TCombobox", "background", ("active",)) == C["dpurp"]
    assert style.lookup("TCombobox", "background", ("!active",)) == C["acc"]
    # 字段内呼吸感（clam padding）
    assert style.lookup("TCombobox", "padding") != ""


@skip_if_no_tk
def test_dropdown_popdown_options_from_tokens(tk_session_root):
    """弹层 option_add 的全部值来自令牌：panel 底 / acc 选中 / 行距呼吸感。"""
    from config.fonts import init_fonts
    from config.theme import DARK_THEME as C

    init_fonts()
    from ui.components.dropdown import install_dropdown_style

    calls: dict[str, str] = {}
    with patch.object(tk_session_root, "option_add", side_effect=lambda k, v: calls.__setitem__(k, str(v))):
        install_dropdown_style(tk_session_root)

    assert calls["*TCombobox*Listbox.background"] == C["panel"]
    assert calls["*TCombobox*Listbox.foreground"] == C["text"]
    assert calls["*TCombobox*Listbox.selectBackground"] == C["acc"]
    assert calls["*TCombobox*Listbox.selectForeground"] == "white"  # 算法极点白
    assert calls["*TCombobox*Listbox.activestyle"] == "none"
    assert calls["*TCombobox*Listbox.spacing3"] == "3"


@skip_if_no_tk
def test_dropdown_style_idempotent(tk_session_root):
    """重复安装不抛错、主题保持 clam（App 重构建场景）。"""
    from tkinter import ttk

    from config.fonts import init_fonts

    init_fonts()
    from ui.components.dropdown import install_dropdown_style

    install_dropdown_style(tk_session_root)
    install_dropdown_style(tk_session_root)
    assert ttk.Style(tk_session_root).theme_use() == "clam"


@pytest.mark.parametrize("attr", ["install_dropdown_style"])
def test_export_exists(attr):
    from ui.components import dropdown

    assert hasattr(dropdown, attr)
