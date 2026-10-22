"""
ui/canvas_image.py — Canvas 图片的描边辅助
──────────────────────────────────────────────
深色画布上的图片没有边界线索：深色图（`#28282c`）落在 `#111827`
画布上只有 1.21:1，图与画布的边缘几乎消失，只剩四周的留白在暗示
范围。

给图片加一圈 1px 的白色低透明度描边即可。Canvas 图元不支持 alpha，
所以按「白色 10% 叠在画布底色上」预先混出实色，视觉等价且不受
图元堆叠顺序影响。

描边色随画布底色变化，而不是全应用一个固定值——描边压在画布上，
换底色就必须重算，否则会在浅一档的画布上偏亮、深一档上偏暗。
"""

from __future__ import annotations

import tkinter as tk

# 描边 = 白色按此比例叠在画布底色上
_OUTLINE_WHITE_MIX = 0.10


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    value = value.lstrip("#")
    if len(value) != 6:
        return None
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


def outline_color(bg: str) -> str:
    """画布底色 → 叠了白色 10% 的描边色。"""
    rgb = _hex_to_rgb(bg)
    if rgb is None:
        return "#ffffff"
    return "#%02x%02x%02x" % tuple(
        max(0, min(255, round(v + (255 - v) * _OUTLINE_WHITE_MIX))) for v in rgb
    )


def outline_bounds(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
    """居中图片（`anchor="center"`）的 1px 描边矩形坐标。

    右下角各减 1，让描边压住图片最外一圈像素，而不是画到图片外面
    去多占一行——图片本身没有留白可吃，多占一行会在紧贴的布局里
    改变视觉尺寸。
    """
    half_w = width // 2
    half_h = height // 2
    return (x - half_w, y - half_h, x - half_w + width - 1, y - half_h + height - 1)


def draw_image(
    canvas: tk.Canvas,
    x: int,
    y: int,
    photo,
    bg: str,
    *,
    tags: tuple[str, ...] = (),
    outline_tags: tuple[str, ...] = (),
) -> tuple[int, int]:
    """在画布上居中画一张图片并加描边，返回 (图片 id, 描边 id)。

    先画图片再画描边：描边矩形压在图片最外一圈像素上，得到「图片
    边缘被一条 1px 亮线勾出」的效果。反过来（描边在下）会被图片
    完全盖住。
    """
    width, height = photo.width(), photo.height()
    image_id = canvas.create_image(x, y, image=photo, anchor="center", tags=tags)
    outline_id = canvas.create_rectangle(
        *outline_bounds(x, y, width, height),
        outline=outline_color(bg),
        width=1,
        tags=outline_tags,
    )
    return image_id, outline_id


def move_outline(canvas: tk.Canvas, outline_id: int, x: int, y: int, photo) -> None:
    """图片平移/换帧后同步描边矩形。"""
    if outline_id is None or photo is None:
        return
    canvas.coords(outline_id, *outline_bounds(x, y, photo.width(), photo.height()))
