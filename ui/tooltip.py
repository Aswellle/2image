"""
ui/tooltip.py — 悬浮提示共用的时间常量
──────────────────────────────────────────────
应用里有两套悬浮提示：历史侧栏卡片按钮上的纯文本气泡，和词条库
词条上的说明卡。两者的外观不同（一个是单行文字、一个是标题+正文），
但「悬停多久出现、多快淡入、停在什么不透明度」是同一件事，用户
对这两处的时间感知也必须是同一套。

此前两处各自硬编码：侧栏 450ms 延迟 / 16ms×7 帧（≈112ms）线性淡入
到 α=1.0，词条库 300ms 延迟 / 25ms×10 帧（250ms）缓出淡入到
α=0.96。同一种控件同一种意图，出现快慢差 1.5 倍、淡入时长差 2.2 倍，
看起来像是其中一个坏了。

取值：延迟 400ms（避开快速划过），淡入 10 帧 × 15ms ≈ 150ms，
终值 α=0.96（略透，不与真实内容抢注意力）。
"""

from __future__ import annotations

import tkinter as tk

from config.fonts import F
from config.theme import DARK_THEME as C
from config.i18n import _

# 悬停多久后开始显示
DELAY_MS = 400

# 淡入：帧数 × 帧间隔 = 总时长
FADE_FRAMES = 10
FADE_FRAME_MS = 15  # 10 × 15 ≈ 150ms

# 终值不透明度
MAX_ALPHA = 0.96


def fade_alpha(step: int) -> float:
    """第 `step` 帧（0 起）的不透明度：缓出曲线，先快后慢。"""
    if FADE_FRAMES <= 1:
        return MAX_ALPHA
    progress = min(1.0, step / (FADE_FRAMES - 1))
    return MAX_ALPHA * progress**0.55


# ══════════════════════════════════════════════════════════════
#   通用单行悬浮说明（icon-only 按钮等无文本控件的可读名称补充）
# ══════════════════════════════════════════════════════════════
_BUBBLE = None  # 进程级单例气泡：同一时刻只显示一条


def attach_tooltip(widget: tk.Widget, text_key: str) -> None:
    """给控件挂单行悬浮说明。

    icon-only 按钮（Segoe 图标字形）的 text 是 PUA 码点，无法向屏幕
    阅读器传达语义，悬浮说明是 Tkinter 平台上可行的最低成本补充。
    时间常量与侧栏/词条库气泡共用一套（DELAY_MS）。
    """
    state = {"after": None}

    def _show(_event=None):
        global _BUBBLE
        if _BUBBLE is not None and _BUBBLE.winfo_exists():
            return
        bubble = tk.Toplevel(widget)
        bubble.wm_overrideredirect(True)
        tk.Label(
            bubble,
            text=_(text_key),
            font=F["small"],
            bg=C["panel"],
            fg=C["text"],
            padx=8,
            pady=4,
            bd=1,
            relief="solid",
        ).pack()
        x = widget.winfo_rootx() + widget.winfo_width() // 2 - 60
        y = widget.winfo_rooty() + widget.winfo_height() + 6
        bubble.wm_geometry("+%d+%d" % (max(0, x), max(0, y)))
        try:
            bubble.attributes("-topmost", True)
        except tk.TclError:
            pass
        _BUBBLE = bubble

    def _hide(_event=None):
        global _BUBBLE
        if state["after"] is not None:
            try:
                widget.after_cancel(state["after"])
            except Exception:
                pass
            state["after"] = None
        if _BUBBLE is not None:
            try:
                if _BUBBLE.winfo_exists():
                    _BUBBLE.destroy()
            except tk.TclError:
                pass
            _BUBBLE = None

    def _schedule(event=None):
        state["after"] = widget.after(DELAY_MS, _show)

    widget.bind("<Enter>", _schedule)
    widget.bind("<Leave>", _hide)
    widget.bind("<ButtonPress>", _hide)
    widget.bind("<Destroy>", _hide)
