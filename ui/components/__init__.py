"""
ui/components/__init__.py — Reusable UI component library

Standardized widgets that consume design tokens for visual
consistency.  All components accept standard tkinter kwargs
plus token-driven styling.

Usage::

    from ui.components import PrimaryButton, ProviderCard, StatusPill
    btn = PrimaryButton(parent, text="Generate", command=on_click)
    pill = StatusPill(parent, state="success", text="Connected")
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from config.design_tokens import TOKENS, button_colors, status_pill_colors


class PrimaryButton(tk.Button):
    """Primary action button with token-driven styling."""

    def __init__(
        self,
        master,
        text: str = "",
        command: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        colors = button_colors("normal", "primary")
        super().__init__(
            master,
            text=text,
            command=command,
            bg=colors["bg"],
            fg=colors["fg"],
            activebackground=TOKENS.highlight,
            activeforeground=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_md, "bold"),
            bd=0,
            padx=TOKENS.space_lg,
            pady=TOKENS.space_sm,
            cursor="hand2",
            **kwargs,
        )


class SecondaryButton(tk.Button):
    """Secondary action button."""

    def __init__(
        self,
        master,
        text: str = "",
        command: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        colors = button_colors("normal", "secondary")
        super().__init__(
            master,
            text=text,
            command=command,
            bg=colors["bg"],
            fg=colors["fg"],
            activebackground=TOKENS.accent,
            activeforeground=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_md),
            bd=0,
            padx=TOKENS.space_md,
            pady=TOKENS.space_sm,
            cursor="hand2",
            **kwargs,
        )


class DangerButton(tk.Button):
    """Danger/destructive action button."""

    def __init__(
        self,
        master,
        text: str = "",
        command: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        colors = button_colors("normal", "danger")
        super().__init__(
            master,
            text=text,
            command=command,
            bg=colors["bg"],
            fg=colors["fg"],
            activebackground=TOKENS.highlight,
            activeforeground=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_md),
            bd=0,
            padx=TOKENS.space_md,
            pady=TOKENS.space_sm,
            cursor="hand2",
            **kwargs,
        )


class GhostButton(tk.Button):
    """Minimal/ghost button."""

    def __init__(
        self,
        master,
        text: str = "",
        command=None,
        **kwargs,
    ) -> None:
        colors = button_colors("normal", "ghost")
        bg = colors["bg"] if colors["bg"] != "transparent" else TOKENS.surface_panel
        super().__init__(
            master,
            text=text,
            command=command,
            bg=bg,
            fg=colors["fg"],
            activebackground=TOKENS.surface_elevated,
            activeforeground=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_sm),
            bd=0,
            padx=TOKENS.space_sm,
            pady=TOKENS.space_xs,
            cursor="hand2",
            **kwargs,
        )


class StatusPill(tk.Label):
    """Small status indicator pill."""

    def __init__(
        self,
        master,
        state: str = "info",
        text: str = "",
        **kwargs,
    ) -> None:
        colors = status_pill_colors(state)
        super().__init__(
            master,
            text=text,
            bg=colors["bg"],
            fg=colors["fg"],
            font=(TOKENS.font_family, TOKENS.font_size_xs, "bold"),
            padx=TOKENS.space_sm,
            pady=2,
            **kwargs,
        )


class ProviderCard(tk.Frame):
    """Card widget for displaying provider info."""

    def __init__(
        self,
        master,
        name: str = "",
        description: str = "",
        status: str = "info",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            bg=TOKENS.surface_panel,
            highlightbackground=TOKENS.border_subtle,
            highlightthickness=1,
            **kwargs,
        )
        # Name label
        self._name_label = tk.Label(
            self,
            text=name,
            bg=TOKENS.surface_panel,
            fg=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_md, "bold"),
            anchor="w",
        )
        self._name_label.pack(fill="x", padx=TOKENS.space_md, pady=(TOKENS.space_sm, 0))

        # Description
        self._desc_label = tk.Label(
            self,
            text=description,
            bg=TOKENS.surface_panel,
            fg=TOKENS.text_secondary,
            font=(TOKENS.font_family, TOKENS.font_size_sm),
            anchor="w",
        )
        self._desc_label.pack(fill="x", padx=TOKENS.space_md)

        # Status pill
        self._status_pill = StatusPill(self, state=status, text=status.upper())
        self._status_pill.pack(anchor="w", padx=TOKENS.space_md, pady=TOKENS.space_sm)


class ErrorBanner(tk.Frame):
    """Error/info banner for displaying messages."""

    def __init__(
        self,
        master,
        message: str = "",
        level: str = "danger",
        **kwargs,
    ) -> None:
        color = TOKENS.danger if level == "danger" else (TOKENS.warning if level == "warning" else TOKENS.info)
        super().__init__(
            master,
            bg=TOKENS.surface_elevated,
            highlightbackground=color,
            highlightthickness=1,
            **kwargs,
        )
        self._icon = tk.Label(
            self,
            text="⚠" if level != "info" else "ℹ",
            bg=TOKENS.surface_elevated,
            fg=color,
            font=(TOKENS.font_family, TOKENS.font_size_lg),
        )
        self._icon.pack(side="left", padx=TOKENS.space_sm)

        self._msg = tk.Label(
            self,
            text=message,
            bg=TOKENS.surface_elevated,
            fg=TOKENS.text_primary,
            font=(TOKENS.font_family, TOKENS.font_size_sm),
            anchor="w",
        )
        self._msg.pack(side="left", fill="x", expand=True, padx=TOKENS.space_xs)

    def set_message(self, message: str, level: str = "danger") -> None:
        color = TOKENS.danger if level == "danger" else (TOKENS.warning if level == "warning" else TOKENS.info)
        self._msg.config(text=message)
        self._icon.config(text="⚠" if level != "info" else "ℹ", fg=color)


class EmptyState(tk.Frame):
    """Empty state placeholder."""

    def __init__(
        self,
        master,
        message: str = "No items",
        **kwargs,
    ) -> None:
        super().__init__(master, bg=TOKENS.surface_app, **kwargs)
        self._icon = tk.Label(
            self,
            text="📭",
            bg=TOKENS.surface_app,
            fg=TOKENS.text_muted,
            font=(TOKENS.font_family, TOKENS.font_size_2xl),
        )
        self._icon.pack(pady=TOKENS.space_xl)

        self._msg = tk.Label(
            self,
            text=message,
            bg=TOKENS.surface_app,
            fg=TOKENS.text_muted,
            font=(TOKENS.font_family, TOKENS.font_size_md),
        )
        self._msg.pack()


class LoadingIndicator(tk.Frame):
    """Animated loading indicator."""

    def __init__(
        self,
        master,
        text: str = "Loading...",
        **kwargs,
    ) -> None:
        super().__init__(master, bg=TOKENS.surface_app, **kwargs)
        self._label = tk.Label(
            self,
            text=text,
            bg=TOKENS.surface_app,
            fg=TOKENS.text_secondary,
            font=(TOKENS.font_family, TOKENS.font_size_sm),
        )
        self._label.pack()
        self._dots = 0
        self._after_id = None


def bind_wraplength(card: "tk.Frame", labels: list, padx_total: int = 32, floor: int = 200) -> None:
    """把标签换行宽度绑定到容器实际宽度（信息卡长行自适应折行）。

    无 wraplength 的超宽标签会被 Tk 在行内居中导致两端同时被裁切；
    padx_total 为标签左右内边距之和（缺省 padx=16×2），floor 防止
    极窄容器下 wraplength 归零。
    """

    def _apply(event):
        wrap = max(floor, event.width - padx_total - 8)
        for lbl in labels:
            lbl.config(wraplength=wrap)

    card.bind("<Configure>", _apply)


def mapped_children_width(row: "tk.Widget", exclude: "tk.Widget | None" = None) -> int:
    """行内已 pack 子项的请求宽度总和（含各自左右 padx）。

    用于「宽度不足时收起次要提示」的自适应判断：按实际子项测量，
    替代按某一语言文案实测出的魔法常数——双语（或字体变化）下
    子项宽度不同，硬编码常数只对一种语言成立。仅统计 pack 管理
    的子项（grid 子项 pack_info 会抛 TclError，跳过）。
    """
    total = 0
    for child in row.winfo_children():
        if child is exclude:
            continue
        try:
            padx = child.pack_info().get("padx", 0)
        except tk.TclError:
            continue
        pad = sum(padx) if isinstance(padx, tuple) else padx * 2
        total += child.winfo_reqwidth() + pad
    return total


def bind_follower_wrap(parent: "tk.Widget", follower: "tk.Label", leaders: list, extra: int = 40, floor: int = 120):
    """行尾跟随标签的换行宽度绑定到「父容器宽 − 前导控件请求宽」。

    同行布局（徽标/标题 + 跟随说明文本）里，长文案（英文界面）
    的标签请求宽超过前导控件占位后的剩余空间时，pack 会把它裁得
    两头都不完整。把 follower 的 wraplength 动态绑定到剩余空间后，
    跟随文本在行内自然折行，双语均不裁切；follower 需已 pack
    （side 与 anchor 由调用方按视觉位置决定）。
    """

    def _apply(_event=None):
        avail = parent.winfo_width()
        for leader in leaders:
            try:
                avail -= leader.winfo_reqwidth()
            except tk.TclError:
                pass
        follower.config(wraplength=max(floor, avail - extra))

    parent.bind("<Configure>", _apply)
    _apply()


from ui.components.state_label import GenerationStateLabel

__all__ = [
    "bind_wraplength",
    "mapped_children_width",
    "bind_follower_wrap",
    "PrimaryButton",
    "SecondaryButton",
    "DangerButton",
    "GhostButton",
    "StatusPill",
    "ProviderCard",
    "ErrorBanner",
    "EmptyState",
    "LoadingIndicator",
    "GenerationStateLabel",
]
