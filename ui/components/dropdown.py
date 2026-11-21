"""
ui/components/dropdown.py — 全局下拉框视觉
──────────────────────────────────────────
ttk.Combobox 的视觉统一入口：主界面 / 提示词助手维度行 / 历史下拉 /
设置窗口 / 付费向导模型下拉共用同一 Tk 实例的 style，故在 App 构建
期调用一次 install_dropdown_style(root) 即全局生效。

设计语言（全部从 config.theme 的 DARK_THEME 令牌派生，无孤立色值）：
  · 字段    entry 底 + sep 边框；获焦时四周亮起 ok 绿边——与 Entry
            的绿边获焦（_gb）同一语言，暗示"此处可交互"
  · 箭头区  常态 acc；hover 提亮为 dpurp（紫系辅助色）——替换此前
            借用主色 hl 的刺眼 hover，语义回归"可展开"
  · 弹出列表 panel 底（与信息卡同层、比字段更沉），行间距 spacing
            增加呼吸感，去 clam 默认的虚线焦点框
  · 选中行  acc 底 + 白字
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from config.fonts import F
from config.theme import DARK_THEME as C


def install_dropdown_style(root: tk.Tk | tk.Toplevel) -> None:
    """配置全局 TCombobox 的字段/箭头/弹出列表视觉（幂等，可重复调用）。"""
    style = ttk.Style(root)
    if style.theme_use() != "clam":
        # clam 才支持 bordercolor/lightcolor/darkcolor 的状态映射
        style.theme_use("clam")

    # ── 字段与箭头 ─────────────────────────────────────────────
    style.configure(
        "TCombobox",
        fieldbackground=C["entry"],
        background=C["acc"],  # 箭头区常态
        foreground=C["text"],
        arrowcolor=C["text"],
        selectbackground=C["acc"],
        selectforeground="white",  # 算法极点白：选中反白
        insertcolor=C["text"],
        bordercolor=C["sep"],
        lightcolor=C["entry"],
        darkcolor=C["entry"],
        padding=(10, 5),  # 字段内呼吸感
    )
    style.map(
        "TCombobox",
        fieldbackground=[
            ("readonly", "focus", C["entry"]),
            ("readonly", "!focus", C["entry"]),
            ("focus", C["entry"]),
            ("!focus", C["entry"]),
            ("disabled", C["panel"]),
        ],
        foreground=[
            ("readonly", C["text"]),
            ("focus", C["text"]),
            ("disabled", C["sub"]),
        ],
        selectbackground=[("focus", C["acc"]), ("!focus", C["acc"])],
        selectforeground=[("focus", "white"), ("!focus", "white")],
        # 获焦绿边：与 Entry 获焦（_gb）同语言
        bordercolor=[("focus", C["ok"]), ("!focus", C["sep"])],
        lightcolor=[("focus", C["ok"]), ("!focus", C["entry"])],
        darkcolor=[("focus", C["ok"]), ("!focus", C["entry"])],
        # 箭头区：hover 提亮为紫系，替换此前借用主色 hl 的刺眼 hover
        background=[("active", C["dpurp"]), ("!active", C["acc"])],
        arrowcolor=[
            ("disabled", C["sub"]),
            ("active", "white"),
            ("!active", C["text"]),
        ],
    )

    # ── 弹出下拉列表（ttk.Combobox 的弹层是 tk.Listbox）─────────
    # 须用 option_add 设置；行距 spacing1/spacing3 增加呼吸感，
    # activestyle=none 去掉 clam 默认的虚线焦点框
    root.option_add("*TCombobox*Listbox.background", C["panel"])
    root.option_add("*TCombobox*Listbox.foreground", C["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["acc"])
    root.option_add("*TCombobox*Listbox.selectForeground", "white")
    root.option_add("*TCombobox*Listbox.relief", "flat")
    root.option_add("*TCombobox*Listbox.borderWidth", "0")
    root.option_add("*TCombobox*Listbox.selectBorderWidth", "0")
    root.option_add("*TCombobox*Listbox.highlightThickness", "0")
    root.option_add("*TCombobox*Listbox.activestyle", "none")
    root.option_add("*TCombobox*Listbox.font", F["body"])
    root.option_add("*TCombobox*Listbox.spacing1", 3)
    root.option_add("*TCombobox*Listbox.spacing3", 3)
