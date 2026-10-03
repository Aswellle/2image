"""
ui/components/toast.py — Transient toast notifications (UIUX §64)
─────────────────────────────────────────────────
Bottom-right transient feedback for quick confirmations
(prompt copied, path copied, queued…).  Generation progress
stays in the status bar; toasts are for one-shot acknowledgements.

· 单例 Toplevel 复用，避免反复创建销毁窗口
· 多条消息排队依次显示，不叠加
· 淡入 → 停留 → 淡出；不支持 alpha 的环境下静默降级为直接显示
· show() 内部经 root.after 调度，工作线程调用亦安全
"""
from __future__ import annotations

import tkinter as tk

from config.design_tokens import TOKENS
from config.fonts import F

_FADE_STEP_MS = 16
_FADE_IN_STEPS = 8
_FADE_OUT_STEPS = 12


class ToastManager:
    """右下角瞬态通知管理器（每个应用一个实例）。"""

    LEVELS = ("success", "info", "warning", "error")

    def __init__(self, root: tk.Tk, default_duration_ms: int = 3200):
        self._root = root
        self._duration = default_duration_ms
        self._win: tk.Toplevel | None = None
        self._lbl: tk.Label | None = None
        self._queue: list[tuple[str, str, int]] = []
        self._busy = False
        self._jobs: list[str] = []

    # ── 公共 API ─────────────────────────────────────────────
    def show(self, message: str, level: str = "info",
             duration_ms: int | None = None) -> None:
        """入队一条通知。线程安全：实际显示经 root.after 调度。"""
        if level not in self.LEVELS:
            level = "info"
        self._queue.append((message, level, duration_ms or self._duration))
        self._root.after(0, self._pump)

    # ── 内部：队列泵 ─────────────────────────────────────────
    def _pump(self):
        if self._busy or not self._queue:
            return
        message, level, duration = self._queue.pop(0)
        self._busy = True
        try:
            self._display(message, level, duration)
        except tk.TclError:
            self._busy = False

    def _display(self, message: str, level: str, duration: int):
        if self._win is None or not self._win.winfo_exists():
            win = tk.Toplevel(self._root)
            win.wm_overrideredirect(True)
            try:
                win.wm_attributes("-topmost", True)
            except tk.TclError:
                pass
            frm = tk.Frame(win, bg=TOKENS.surface_elevated,
                           highlightbackground=TOKENS.border_subtle,
                           highlightthickness=1)
            frm.pack(fill="both", expand=True)
            self._lbl = tk.Label(frm, font=F["body"], padx=16, pady=10,
                                 justify="left", anchor="w")
            self._lbl.pack()
            self._win = win

        colors = self._colors_for(level)
        self._lbl.config(text=message, bg=colors["bg"], fg=colors["fg"])
        self._lbl.update_idletasks()
        self._position()
        self._fade(1.0 / _FADE_IN_STEPS, _FADE_IN_STEPS,
                   lambda: self._jobs.append(
                       self._root.after(duration, self._fade_out)))

    def _colors_for(self, level: str) -> dict:
        return {
            "success": {"bg": TOKENS.success, "fg": TOKENS.text_inverse},
            "info":    {"bg": TOKENS.surface_elevated, "fg": TOKENS.text_primary},
            "warning": {"bg": TOKENS.warning, "fg": TOKENS.text_inverse},
            "error":   {"bg": TOKENS.danger, "fg": TOKENS.text_inverse},
        }.get(level, {"bg": TOKENS.surface_elevated, "fg": TOKENS.text_primary})

    def _position(self):
        if self._win is None:
            return
        try:
            self._win.update_idletasks()
            w = self._win.winfo_reqwidth()
            h = self._win.winfo_reqheight()
            x = self._root.winfo_x() + self._root.winfo_width() - w - 24
            y = self._root.winfo_y() + self._root.winfo_height() - h - 48
            self._win.wm_geometry(f"+{max(0, x)}+{max(0, y)}")
            self._win.deiconify()
        except tk.TclError:
            pass

    def _set_alpha(self, alpha: float):
        if self._win is None:
            return
        try:
            self._win.wm_attributes("-alpha", alpha)
        except tk.TclError:
            pass

    def _fade(self, step: float, steps: int, done, alpha: float = 0.0):
        alpha = min(1.0, alpha + step)
        self._set_alpha(alpha)
        if steps > 1:
            self._jobs.append(self._root.after(
                _FADE_STEP_MS,
                lambda: self._fade(step, steps - 1, done, alpha)))
        else:
            done()

    def _fade_out(self):
        self._fade(-1.0 / _FADE_OUT_STEPS, _FADE_OUT_STEPS, self._finish_current,
                   alpha=1.0)

    def _finish_current(self):
        self._set_alpha(0.0)
        if self._win is not None:
            try:
                self._win.withdraw()
            except tk.TclError:
                pass
        self._busy = False
        self._pump()

    def close_current(self):
        """立即结束当前通知（测试与极端情况使用）。"""
        for job in self._jobs:
            try:
                self._root.after_cancel(job)
            except Exception:
                pass
        self._jobs.clear()
        self._finish_current()

    def pending_count(self) -> int:
        return len(self._queue) + (1 if self._busy else 0)
