"""
config/ui_geometry.py — 高 DPI 窗口几何缩放
────────────────────────────────────────────
DPI 感知进程下，Tk 字体随系统缩放放大（150% 缩放下 tk scaling≈2.0，
字体为 96dpi 基准的 1.5 倍），而各窗口的固定几何值（如 1380x920）
如果不随之缩放，内容会按物理像素挤在未放大的窗口里溢出被裁。

本模块把「96dpi 基准的几何值」按当前 tk scaling 归一放大，并在需要
时钳制到屏幕工作区：

    ui_scale(root)          — 缩放系数（96dpi 机器恒为 1.0，行为不变）
    scaled(root, px)        — 单值几何（宽/高/边距）按系数放大
    fit_to_workarea(root, …) — 放大后钳制到屏幕，返回 (w, h)
    centered_geometry(parent, w, h) — 相对父窗口居中的 geometry 串

只缩放「窗口外框几何」：控件内容尺寸（字体、按钮内边距、请求宽）
由 Tk 按字体自动放大，运行时实测的自适应逻辑（wraplength 绑定、
工具行收纳判定）不受影响。
"""

from __future__ import annotations

import tkinter as tk

# Tk 在 96dpi（100% 缩放）下的默认 scaling 值；高于此值的部分即系统缩放
_BASE_SCALING = 4.0 / 3.0


def ui_scale(root: tk.Misc | tk.Tk) -> float:
    """当前缩放系数：96dpi 机器恒为 1.0，150% 缩放约 1.5。"""
    try:
        scaling = float(root.tk.call("tk", "scaling"))
    except Exception:
        return 1.0
    return max(1.0, scaling / _BASE_SCALING)


def scaled(root: tk.Misc | tk.Tk, px: int) -> int:
    """96dpi 基准的几何值 → 当前缩放下的物理像素值（只放大不缩小）。"""
    return max(int(px), int(round(px * ui_scale(root))))


def fit_to_workarea(root: tk.Misc | tk.Tk, w: int, h: int, reserve: int = 48) -> tuple[int, int]:
    """放大后的窗宽高钳制到屏幕（感知进程下屏幕尺寸为物理像素）。

    reserve 为任务栏与窗口装饰的纵向余量；下限防止极端小屏时窗口
    被钳到不可用。
    """
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    return (
        min(w, max(640, int(sw * 0.98))),
        min(h, max(520, sh - reserve)),
    )


def centered_geometry(parent: tk.Misc, w: int, h: int) -> str:
    """以父窗口为中心的 geometry 串（含缩放与屏幕钳制后的坐标）。"""
    x = max(0, parent.winfo_x() + (parent.winfo_width() - w) // 2)
    y = max(0, parent.winfo_y() + (parent.winfo_height() - h) // 2)
    return f"{w}x{h}+{max(0, x)}+{max(0, y)}"
