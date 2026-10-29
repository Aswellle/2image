"""
ui/icons.py — 单色矢量图标系统（Segoe Fluent Icons / Segoe MDL2 Assets）
──────────────────────────────────────────────────────────────────────
Windows 10/11 系统自带图标字体，Tk 直接以字体渲染 PUA 码位：

  • 位图图标在 125%/150% DPI 下会发糊，字体字形随 DPI 锐利缩放；
  • 颜色随控件 fg 走主题令牌，与调色板天然一致（emoji 是固彩，
    与 navy 单色 UI 相冲突）；
  • 零依赖、零资产管线（无需打包 SVG/PNG，也不用新增光栅化库）。

字体解析顺序：Segoe Fluent Icons（Win11）→ Segoe MDL2 Assets
（Win10）→ Segoe UI Emoji（兜底：码位缺失时维持 emoji 外观能力）。

注意：码位位于 PUA 私有区，必须用 icon_font() 渲染——混入中文
字体（微软雅黑）会显示为方框。

Usage::

    from ui.icons import glyph, icon_font
    tk.Button(parent, text=glyph("trash"), font=icon_font(11), fg=C["sub"], ...)
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

_FAMILY: str | None = None

# 候选字体族：Win11 先，Win10 兜底
_CANDIDATES = ("Segoe Fluent Icons", "Segoe MDL2 Assets")

# 语义名 → Segoe MDL2 Assets 码位（全部经截图网格逐码位目视验证）
_GLYPHS: dict[str, str] = {
    "search": "\ue721",  # Search
    "close": "\ue711",  # Cancel
    "edit": "\ue70f",  # Edit
    "star_fill": "\ue735",  # 实心星（Fluent 下 E736 渲染为书本，勿用）
    "star_outline": "\ue734",  # 空心星
    "tag": "\ue8ec",  # Tag
    "compare": "\ue8ab",  # Switch（左右对换，A/B 对比语义）
    "trash": "\ue74d",  # Delete
    "add": "\ue710",  # Add
    "checkmark": "\ue73e",  # CheckMark
    "eye": "\ue7b3",  # RedEye
    "eye_off": "\ued1a",  # Hide
    "image": "\ueb9f",  # Photo2
    "clock": "\ue823",  # Recent（等待语义；字体族内无沙漏字形）
    "stopwatch": "\ue916",  # Stopwatch
    "copy": "\ue8c8",  # Copy
    "save": "\ue74e",  # Save
    "calendar": "\ue787",  # Calendar
    "sun": "\ue706",  # Sunny
    "folder_open": "\ue838",  # FolderOpen
    "refresh": "\ue72c",  # Refresh
    "crop": "\ue7a8",  # Crop
    "download": "\ue896",  # Download
    "camera": "\ue722",  # Camera
    "settings": "\ue713",  # Setting
}


def resolve_family() -> str:
    """解析可用的图标字体族（结果缓存）；找不到时退回 emoji 字体。"""
    global _FAMILY
    if _FAMILY is None:
        try:
            families = set(tkfont.families())
        except tk.TclError:
            families = set()
        _FAMILY = next((f for f in _CANDIDATES if f in families), "Segoe UI Emoji")
    return _FAMILY


def glyph(name: str) -> str:
    """按语义名取图标字符；未知名称返回空串（调用方决定兜底）。"""
    return _GLYPHS.get(name, "")


def icon_font(size: int) -> tuple[str, int]:
    """图标控件专用字体；icon_font(11) 对齐 F["input"] 的视觉大小。"""
    return (resolve_family(), size)
