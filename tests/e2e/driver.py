"""
tests/e2e/driver.py — 端到端交互驱动
────────────────────────────────────
模拟真实用户操作的工具层：事件级（event_generate，无需真实指针）与
控件级（invoke / config）双轨。所有断言前用 pump 泵主循环，后台线程
回调（root.after 派发）用 wait_until 轮询消化。

设计约束：
  · 不引入第三方 GUI 自动化依赖，纯 tkinter 事件机制
  · App 以 withdrawn Toplevel 承载（会话根），几何/焦点/事件全部可用
  · 类型宽容：接受任意 tk.Widget，出错抛清晰断言信息
"""

from __future__ import annotations

import time
import tkinter as tk
from typing import Callable


def pump(widget: tk.Misc, times: int = 5) -> None:
    """泵主循环若干次，消化 after 队列与几何布局。"""
    root = widget.winfo_toplevel()
    for _ in range(times):
        try:
            root.update()
        except tk.TclError:
            return


def wait_until(
    widget: tk.Misc,
    predicate: Callable[[], bool],
    timeout_ms: int = 8000,
    interval_ms: int = 25,
) -> bool:
    """泵事件直到条件成立；超时返回 False（由调用方断言）。

    Tcl 单线程约束：后台线程的 root.after 派发只有在解释器处于
    事件循环期间才合法（否则 "main thread is not in main loop"）。
    因此等待期间用「定时 quit 的突发 mainloop」让主线程持续处理
    事件，后台生成线程的回调得以正常注册与执行。
    """
    root = widget.winfo_toplevel()
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        try:
            root.update()
        except tk.TclError:
            return False
        try:
            if predicate():
                return True
        except tk.TclError:
            return False
        try:
            root.after(int(interval_ms), root.quit)
            root.mainloop()
        except tk.TclError:
            return False
    try:
        root.update()
    except tk.TclError:
        return False
    try:
        return bool(predicate())
    except tk.TclError:
        return False


def focus(widget: tk.Widget) -> None:
    widget.focus_set()
    pump(widget)


def click(widget: tk.Widget, x: int = 4, y: int = 4) -> None:
    """模拟一次左键点击（进入→按下→释放→离开）。"""
    widget.update_idletasks()
    widget.event_generate("<Enter>", x=x, y=y)
    widget.event_generate("<ButtonPress-1>", x=x, y=y)
    widget.event_generate("<ButtonRelease-1>", x=x, y=y)
    pump(widget)


def double_click(widget: tk.Widget, x: int = 4, y: int = 4) -> None:
    widget.event_generate("<Double-Button-1>", x=x, y=y)
    pump(widget)


def right_click(widget: tk.Widget, x: int = 4, y: int = 4) -> None:
    widget.event_generate("<ButtonPress-3>", x=x, y=y)
    widget.event_generate("<ButtonRelease-3>", x=x, y=y)
    pump(widget)


def set_entry(entry: tk.Entry, text: str) -> None:
    """清空并输入 Entry 文本（insert 会同步 textvariable 并触发 trace）。"""
    entry.focus_set()
    state = str(entry.cget("state"))
    if state == "readonly":
        entry.config(state="normal")
    entry.delete(0, "end")
    entry.insert(0, text)
    entry.event_generate("<KeyRelease>")
    if state == "readonly":
        entry.config(state="readonly")
    pump(entry)


def type_into_text(text_widget: tk.Text, text: str) -> None:
    """向 Text 控件追加文本（<<Modified>> 自动触发字符计数等绑定）。"""
    text_widget.focus_set()
    text_widget.insert("end", text)
    pump(text_widget)


def clear_text(text_widget: tk.Text) -> None:
    text_widget.delete("1.0", "end")
    pump(text_widget)


def press_key(widget: tk.Widget, sequence: str) -> None:
    """向获得焦点的控件生成按键事件（如 '<Return>' / '<Escape>'）。

    Toplevel 级绑定（Escape 关窗等）用窗口对象调用本函数。
    """
    widget.focus_set()
    widget.event_generate(sequence)
    pump(widget)


def invoke_btn(button: tk.Widget) -> None:
    """直接调用按钮 command（比事件模拟更稳，等同用户点击的最终效果）。"""
    res = button.invoke()
    pump(button)
    return res


def set_combobox(combo: ttk_combobox(), value: str) -> None:
    """设置只读组合框值并派发 <<ComboboxSelected>>。"""
    combo.set(value)
    combo.event_generate("<<ComboboxSelected>>")
    pump(combo)


def combobox_value(combo) -> str:
    return combo.get()


def find_buttons(root: tk.Misc, text: str | None = None) -> list:
    """按文本（精确或子串）在控件树里找 tk.Button。"""
    found = []

    def _walk(w):
        for ch in w.winfo_children():
            if isinstance(ch, tk.Button):
                t = str(ch.cget("text"))
                if text is None or text in t:
                    found.append(ch)
            _walk(ch)

    _walk(root)
    return found


def find_toplevels(root: tk.Misc, title: str | None = None) -> list:
    """找当前存活的 Toplevel（按标题过滤）。"""
    found = []
    for ch in root.winfo_children():
        if isinstance(ch, tk.Toplevel):
            if title is None or title in str(ch.title()):
                found.append(ch)
    return found


def toplevel_by_title(root: tk.Misc, title: str):
    tops = find_toplevels(root, title)
    return tops[0] if tops else None


def ttk_combobox():
    from tkinter import ttk

    return ttk.Combobox
