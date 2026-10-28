"""
ui/button_states.py — Tk button interaction-state defaults
──────────────────────────────────────────────────────────────
`tk.Button` 在 `bd=0` 时唯一的按压反馈就是背景色，而 Tk 的
`-activebackground` / `-activeforeground` / `-disabledforeground`
默认取自 Windows 系统色（`SystemButtonFace` #f0f0f0、
`SystemButtonText` 黑、`SystemDisabledText` #6d6d6d）。本项目
每个按钮都自绘了深色底，系统色一旦生效就是一块白闪 + 不可读
的文字——实测 `#6d6d6d` 落在 `#e94560` 上只有 1.35:1。

本模块提供两件事：

1. `install_button_state_defaults(root)` —— `<Map>` 类绑定，任何
   按钮第一次上屏时补齐它没显式设置的按压态颜色，并在按钮
   「构造即禁用」时直接套用禁用态配色。对话框 / wizard / 面板
   都是运行时创建的，所以只能用类绑定，不能在启动时遍历一遍。

2. `set_enabled(btn, enabled)` —— 运行时切换可用态的唯一入口。
   禁用时把底色与文字一起压暗（亮度降下来但对比度升上去），
   恢复时写回常态配色。直接 `.config(state="disabled")` 会让
   标签落在原本的高饱和底色上，`#6d6d6d` 之类的系统灰在
   `#e94560` 上只有 1.35:1。

显式设置过 `-activebackground` 等选项的按钮不受影响（如 ⊕ 按钮
刻意用绿色按压反馈）。

放在 `ui/` 而不是 `config/`：它操作 Tk 控件，属于 UI 层。
"""

from __future__ import annotations

import tkinter as tk

from config.theme import DARK_THEME as C


# 按压色 = 常态底色压暗的比例；近黑底色改用向白提亮，否则压暗不可见
_PRESS_DIM = 0.86
_PRESS_LIFT = 0.14
_NEAR_BLACK_LUMINANCE = 0.06

# 禁用态：底色向面板色靠拢 55%，文字与底色混合 30% 起，再按需
# 向对比度更高的方向推到 4.5:1（WCAG AA 正文）
_DISABLED_BG_MIX = 0.55
_DISABLED_FG_MIX = 0.30
_DISABLED_MIN_CONTRAST = 4.5
# 图标按钮（✏ ★ 🏷 ⚖ 🗑 等单/双字符）按图形对象算，WCAG 要求 3:1
_ICON_MIN_CONTRAST = 3.0

# 常态配色缓存在控件上，供 set_enabled(True) 还原
_NORMAL_ATTR = "_ql_normal_palette"


# ─── 颜色工具 ─────────────────────────────────────────────────────


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    value = value.lstrip("#")
    if len(value) != 6:
        return None
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


def _rgb_to_hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in rgb)


def _relative_luminance(rgb) -> float:
    """WCAG 相对亮度（0–255 的 sRGB 分量）。"""

    def lin(v: float) -> float:
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    """两色的 WCAG 对比度；解析失败时返回 0（视为不合格）。"""
    a, b = _hex_to_rgb(fg), _hex_to_rgb(bg)
    if a is None or b is None:
        return 0.0
    la, lb = _relative_luminance(a), _relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _mix(a: str, b: str, t: float) -> str:
    """线性插值：t=0 得到 a，t=1 得到 b。"""
    ca, cb = _hex_to_rgb(a), _hex_to_rgb(b)
    if ca is None or cb is None:
        return a
    return _rgb_to_hex([ca[i] + (cb[i] - ca[i]) * t for i in range(3)])


def _resolve(widget: tk.Misc, color: str) -> str | None:
    """把 Tk 颜色名（SystemButtonFace 等）解析成 #rrggbb。"""
    if _hex_to_rgb(color) is not None:
        return color
    try:
        raw = widget.winfo_rgb(color)
    except (tk.TclError, AttributeError):
        # AttributeError：非 Tk 控件（测试替身）
        return None
    return _rgb_to_hex([raw[0] // 257, raw[1] // 257, raw[2] // 257])


# ─── 派生色 ───────────────────────────────────────────────────────


def press_color(widget: tk.Misc | None, bg: str) -> str:
    """由按钮常态底色派生按压底色。

    暗底压暗 14%，近黑底向白提亮 14% —— 两种情况下按压都有
    可见的方向变化，不会因为底色本身已经接近纯黑而「按了没反应」。
    """
    resolved = _resolve(widget, bg) if widget is not None else (_hex_to_rgb(bg) and bg)
    rgb = _hex_to_rgb(resolved) if resolved else None
    if rgb is None:
        return bg
    if _relative_luminance(rgb) < _NEAR_BLACK_LUMINANCE:
        out = [v + (255 - v) * _PRESS_LIFT for v in rgb]
    else:
        out = [v * _PRESS_DIM for v in rgb]
    return _rgb_to_hex(out)


def disabled_bg(bg: str) -> str:
    """禁用态底色：向面板色靠拢，保留一点原色相。"""
    return _mix(bg, C["panel"], _DISABLED_BG_MIX)


def disabled_fg(fg: str, bg: str) -> str:
    """禁用态文字色：先压暗，再按需推向白/黑直到满足 4.5:1。

    只压暗不校验会在亮底（`#e94560`、`#34d399`）上掉到 1.x:1；
    只套固定灰（`#94a3b8`）同样在亮底上不合格。所以以「压暗后的
    文字」为起点，朝离底色更远的一极逐步推移。
    """
    base = _mix(fg, bg, _DISABLED_FG_MIX)
    if contrast_ratio(base, bg) >= _DISABLED_MIN_CONTRAST:
        return base
    rgb_bg = _hex_to_rgb(bg)
    if rgb_bg is None:
        return C["text_disabled"]
    pole = "#ffffff" if _relative_luminance(rgb_bg) < 0.35 else "#000000"
    for step in range(1, 11):
        candidate = _mix(base, pole, step / 10)
        if contrast_ratio(candidate, bg) >= _DISABLED_MIN_CONTRAST:
            return candidate
    return pole


# ─── 常态配色缓存 ─────────────────────────────────────────────────


def _stash_normal(widget: tk.Button) -> tuple[str, str]:
    """记录按钮的常态配色；已记录过则原样返回。"""
    stashed = getattr(widget, _NORMAL_ATTR, None)
    if stashed is not None:
        return stashed
    stashed = (widget.cget("background"), widget.cget("foreground"))
    setattr(widget, _NORMAL_ATTR, stashed)
    return stashed


def _is_unset(value: str, system_default: str) -> bool:
    """选项是否仍停留在 Tk 的系统默认值。"""
    return str(value).strip().lower() in ("", system_default.lower())


def readable_on(widget: tk.Misc, fg: str, bg: str, minimum: float | None = None) -> str:
    """在 `bg` 上尽量保留 `fg`；不达标时改用黑白中更清晰的一极。

    按压态的底色常常与常态不同色相（如卡片上的 🗑 常态透明、
    按压变红），直接沿用常态文字色会出现红字压红底（1.38:1）。
    """
    resolved_fg = _resolve(widget, fg) or fg
    resolved_bg = _resolve(widget, bg) or bg
    floor = _DISABLED_MIN_CONTRAST if minimum is None else minimum
    if contrast_ratio(resolved_fg, resolved_bg) >= floor:
        return fg
    return max(("#ffffff", "#000000"), key=lambda c: contrast_ratio(c, resolved_bg))


def _label_contrast_floor(widget: tk.Button) -> float:
    """图标按钮按 3:1（图形对象），有文字的按 4.5:1（正文）。

    ✏ ★ 🏷 ⚖ 🗑 这类单字符按钮的「文字」其实是图标，WCAG 对
    图形对象要求 3:1；按 4.5:1 会把它逼成黑字压在红底上。
    """
    try:
        label = str(widget.cget("text")).strip()
    except tk.TclError:
        return _DISABLED_MIN_CONTRAST
    return _ICON_MIN_CONTRAST if len(label) <= 2 else _DISABLED_MIN_CONTRAST


def _apply_disabled_palette(widget: tk.Button, bg: str | None = None) -> None:
    """把按钮切成禁用外观：底色压暗 + 文字重新取色。"""
    if not hasattr(widget, "winfo_rgb"):
        # 非 Tk 控件（测试替身）只保证 state 语义
        widget.config(state="disabled")
        return
    normal_bg, normal_fg = _stash_normal(widget)
    # Tk 接受 "white" / "SystemButtonFace" 这类颜色名，先解析成
    # #rrggbb，否则 _mix / contrast_ratio 拿不到数值会直接放弃。
    base_bg = _resolve(widget, bg or normal_bg) or normal_bg
    base_fg = _resolve(widget, normal_fg) or normal_fg
    target_bg = disabled_bg(base_bg)
    widget.config(
        state="disabled",
        bg=target_bg,
        disabledforeground=disabled_fg(base_fg, target_bg),
        cursor="",
    )


# ─── 对外接口 ─────────────────────────────────────────────────────


def apply_state_defaults(widget: tk.Widget) -> None:
    """补齐单个按钮没显式设置的按压/禁用态颜色。

    「构造即禁用」的按钮（如批量面板的保留/丢弃、更新对话框的
    安装按钮）在第一次上屏时就直接套用禁用配色，否则它们的高
    饱和底色会一直配着系统灰文字。
    """
    if not isinstance(widget, tk.Button):
        return
    try:
        _stash_normal(widget)
        if _is_unset(widget.cget("activebackground"), "SystemButtonFace"):
            widget.config(activebackground=press_color(widget, widget.cget("background")))
        if _is_unset(widget.cget("activeforeground"), "SystemButtonText"):
            # 按压底色可能与常态差很远（透明卡片按钮按下变红），
            # 沿用常态文字色会撞色，所以按按压底色重新挑一次
            widget.config(
                activeforeground=readable_on(
                    widget,
                    widget.cget("foreground"),
                    widget.cget("activebackground"),
                    minimum=_label_contrast_floor(widget),
                )
            )
        if _is_unset(widget.cget("disabledforeground"), "SystemDisabledText"):
            widget.config(disabledforeground=C["text_disabled"])
        if str(widget.cget("state")) == "disabled":
            _apply_disabled_palette(widget)
    except tk.TclError:
        # 控件在回调执行前已被销毁（对话框快速关闭）
        pass


def install_button_state_defaults(root: tk.Misc) -> None:
    """为整棵控件树安装 `<Map>` 兜底。

    用类绑定而不是遍历控件：对话框 / wizard / 面板都是运行时才
    创建的，遍历只能覆盖启动那一刻已经存在的按钮。
    """

    def _on_map(event: tk.Event) -> None:
        apply_state_defaults(event.widget)

    root.bind_class("Button", "<Map>", _on_map, add="+")


def set_enabled(
    btn: tk.Button,
    enabled: bool,
    *,
    bg: str | None = None,
    fg: str | None = None,
    text: str | None = None,
) -> None:
    """切换按钮可用态，并同步底色/文字/指针。

    `bg` / `fg` 在**启用**时改写常态配色（缓存随之更新）；在
    **禁用**时作为禁用态底色覆盖（例如图生图锁定的变体按钮要用
    警示红而不是常态紫）。`text` 两边都会写入。
    """
    if text is not None:
        btn.config(text=text)

    if enabled:
        if not hasattr(btn, "winfo_rgb"):
            btn.config(state="normal")
            return
        normal_bg, normal_fg = _stash_normal(btn)
        new_bg = bg if bg is not None else normal_bg
        new_fg = fg if fg is not None else normal_fg
        setattr(btn, _NORMAL_ATTR, (new_bg, new_fg))
        btn.config(state="normal", bg=new_bg, fg=new_fg, cursor="hand2")
        if _is_unset(btn.cget("activebackground"), "SystemButtonFace"):
            btn.config(activebackground=press_color(btn, new_bg))
        return

    _stash_normal(btn)
    _apply_disabled_palette(btn, bg)
