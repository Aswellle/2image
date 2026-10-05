"""tests/test_language.py — 界面语言切换器回归。

覆盖：语言注册表、set_language 持久化、翻译在重启（init_language）后生效、
偏好对话框保存语义。
"""
from __future__ import annotations

import tkinter as tk

import pytest

from config.i18n import _, init_language, set_language, get_language
from config.settings import DEFAULT_CONFIG


@pytest.fixture(autouse=True)
def _restore_lang():
    """测试后恢复默认语言，避免污染其他用例。"""
    yield
    set_language("zh-CN")


def test_supported_languages_cover_all_locales(app, tk_root):
    a, _ = app
    assert set(a.SUPPORTED_LANGUAGES) == {"zh-CN", "zh-TW", "en"}
    assert a.lang_var.get() == "zh-CN"  # 默认配置


def test_set_language_persists(app, monkeypatch):
    a, saved = app
    import services.application.settings_controller as sc
    captured = {}
    monkeypatch.setattr(sc, "save_config", lambda c: captured.update(dict(c)))
    a.settings_controller.set_language("en")
    assert a.cfg["language"] == "en"
    assert captured.get("language") == "en"


def test_set_language_same_value_is_noop(app, monkeypatch):
    a, saved = app
    calls = []
    monkeypatch.setattr(a, "_toast", lambda m, l="info": calls.append(m))
    a.settings_controller.set_language("zh-CN")   # 与当前一致
    assert calls == []                            # 不提示、不保存
    assert "language" not in saved


def test_set_language_notifies_restart(app, monkeypatch):
    a, _ = app
    toasts = []
    monkeypatch.setattr(a, "_toast", lambda m, l="info": toasts.append((m, l)))
    a.settings_controller.set_language("zh-TW")
    assert len(toasts) == 1
    msg, level = toasts[0]
    assert "重启" in msg or "restart" in msg.lower()
    assert level == "info"


def test_translation_applies_after_init_language():
    """切换语言 + 重启（init_language）后翻译生效。"""
    init_language({"language": "en"})
    assert _("menu_file") == "📁  File"  # 与 menu_tools 等一致带 emoji 前缀
    assert _("settings_language") == "Interface Language"
    init_language({"language": "zh-TW"})
    assert _("menu_file") == "📁  檔案"
    init_language({"language": "zh-CN"})
    assert _("menu_file") == "📁  文件"


def test_unknown_language_falls_back_to_default():
    init_language({"language": "xx-YY"})
    assert get_language() == "zh-CN"   # init_language 对未知代码回落默认


def test_default_config_has_language_key():
    assert DEFAULT_CONFIG.get("language") == "zh-CN"


def test_menu_bar_structure_with_language_submenu(app):
    """顶部菜单五级联 + 文件菜单四动作 + 语言三选（tearoff=0 时 index 从 0 起）。"""
    a, _ = app
    menubar = a.root.nametowidget(a.root.cget("menu"))

    def walk(menu):
        out = []
        for i in range(menu.index("end") + 1):
            t = menu.type(i)
            if t in ("separator", "tearoff"):
                if t == "separator":
                    out.append((t, None, None))
                continue
            label = menu.entrycget(i, "label")
            if t == "cascade":
                out.append((t, label, walk(menu.nametowidget(menu.entrycget(i, "menu")))))
            elif t == "radiobutton":
                out.append((t, label, menu.entrycget(i, "value")))
            else:
                out.append((t, label, None))
        return out

    tree = walk(menubar)
    top_labels = [l for t, l, _ in tree if t == "cascade"]
    assert len(top_labels) == 5
    assert "文件" in top_labels[0] and "工具" in top_labels[1]
    assert "接口配置" in top_labels[2] and "数据" in top_labels[3] and "设置" in top_labels[4]

    file_cmds = [l for t, l, _ in tree[0][2] if t == "command"]
    assert len(file_cmds) == 4 and "查看器" in file_cmds[0]

    settings_sub = tree[4][2]
    lang = next(sub for t, l, sub in settings_sub if t == "cascade" and "界面语言" in l)
    entries = [(l, v) for t, l, v in lang if t == "radiobutton"]
    assert [v for _, v in entries] == ["zh-CN", "zh-TW", "en"]
    assert [l for l, _ in entries] == ["简体中文", "繁體中文", "English"]
