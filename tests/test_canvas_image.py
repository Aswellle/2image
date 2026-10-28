"""tests/test_canvas_image.py — Canvas 图片描边回归。

覆盖：描边色随画布底色派生、描边矩形贴合图片、图元叠放顺序
（描边必须压在图片最外一圈像素上），以及平移/换帧后描边跟随。
"""

from __future__ import annotations

import tkinter as tk

import pytest
from PIL import Image, ImageTk

from ui.canvas_image import draw_image, move_outline, outline_bounds, outline_color


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


# ── 描边色 ──────────────────────────────────────────────────
def test_outline_is_white_ten_percent_over_canvas():
    assert outline_color("#111827") == "#292f3d"
    assert outline_color("#0a0f1a") == "#222731"
    assert outline_color("#0d1a2a") == "#25313f"


def test_outline_lighter_than_canvas():
    for bg in ("#111827", "#0a0f1a", "#0d1a2a", "#000000"):
        canvas_rgb = _hex_to_rgb(bg)
        outline_rgb = _hex_to_rgb(outline_color(bg))
        assert all(o >= c for o, c in zip(outline_rgb, canvas_rgb)), bg


def test_outline_keeps_neutral_hue():
    """描边必须是中性白叠加：叠加后色偏只会收窄，不会引入新倾向。"""
    canvas_rgb = _hex_to_rgb("#0d1a2a")
    outline_rgb = _hex_to_rgb(outline_color("#0d1a2a"))
    canvas_spread = max(canvas_rgb) - min(canvas_rgb)
    outline_spread = max(outline_rgb) - min(outline_rgb)
    assert 0 < outline_spread <= canvas_spread


def test_outline_falls_back_to_white_on_bad_input():
    assert outline_color("not-a-color") == "#ffffff"
    assert outline_color("") == "#ffffff"


# ── 几何 ────────────────────────────────────────────────────
@pytest.mark.parametrize("w,h", [(100, 80), (101, 81), (1, 1), (260, 200)])
def test_outline_bounds_cover_image_extent(w, h):
    cx, cy = 200, 150
    left, top, right, bottom = outline_bounds(cx, cy, w, h)
    assert right - left + 1 == w
    assert bottom - top + 1 == h
    # 居中：图片左右留白差不超过 1px（奇数尺寸）
    assert abs((left - (cx - w // 2)) - ((cx - (right + 1)) + w // 2)) <= 1
    assert abs((top - (cy - h // 2)) - ((cy - (bottom + 1)) + h // 2)) <= 1


# ── Canvas 上的实际叠放 ──────────────────────────────────────
@pytest.fixture
def canvas(tk_root):
    host = tk.Frame(tk_root)
    cv = tk.Canvas(host, bg="#111827", width=300, height=200, bd=0, highlightthickness=0)
    cv.pack()
    host.pack()
    yield cv
    host.destroy()


def _photo(w=60, h=40):
    return ImageTk.PhotoImage(Image.new("RGB", (w, h), (240, 240, 240)))


def test_draw_image_puts_outline_above_image(canvas):
    photo = _photo()
    image_id, outline_id = draw_image(canvas, 150, 100, photo, "#111827")
    # 描边必须后创建（Canvas 图元按创建顺序叠放），否则被图片完全盖住
    assert canvas.find_all().index(outline_id) > canvas.find_all().index(image_id)


def test_draw_image_outline_uses_canvas_bg(canvas):
    photo = _photo()
    _, outline_id = draw_image(canvas, 150, 100, photo, "#111827")
    assert canvas.itemcget(outline_id, "outline").lower() == outline_color("#111827")


def test_draw_image_applies_tags_to_both_items(canvas):
    photo = _photo()
    image_id, outline_id = draw_image(canvas, 150, 100, photo, "#111827", tags=("prev",), outline_tags=("prev",))
    assert "prev" in canvas.gettags(image_id)
    assert "prev" in canvas.gettags(outline_id)
    canvas.delete("prev")
    assert canvas.find_all() == ()


def test_move_outline_follows_the_image(canvas):
    photo = _photo(60, 40)
    _, outline_id = draw_image(canvas, 150, 100, photo, "#111827")
    move_outline(canvas, outline_id, 80, 60, photo)
    assert canvas.coords(outline_id) == list(outline_bounds(80, 60, 60, 40))


def test_move_outline_resizes_for_a_new_frame(canvas):
    photo = _photo(60, 40)
    _, outline_id = draw_image(canvas, 150, 100, photo, "#111827")
    bigger = _photo(120, 80)
    move_outline(canvas, outline_id, 150, 100, bigger)
    assert canvas.coords(outline_id) == list(outline_bounds(150, 100, 120, 80))


def test_move_outline_is_a_noop_before_the_first_frame(canvas):
    move_outline(canvas, None, 10, 10, None)
    assert canvas.find_all() == ()
