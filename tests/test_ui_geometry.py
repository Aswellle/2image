"""tests/test_ui_geometry.py — 高 DPI 窗口几何缩放 helper。

缩放系数来自 tk scaling（96dpi 基准归一）；断言按当前环境的实际
系数计算，不钉死具体数值，任何缩放比例的机器上均成立。
"""

import re

from tests.conftest import skip_if_no_tk


@skip_if_no_tk
def test_ui_scale_at_least_one(tk_session_root):
    from config.ui_geometry import ui_scale

    assert ui_scale(tk_session_root) >= 1.0


@skip_if_no_tk
def test_scaled_never_shrinks(tk_session_root):
    from config.ui_geometry import scaled, ui_scale

    root = tk_session_root
    assert scaled(root, 100) >= 100
    expected = max(100, int(round(100 * ui_scale(root))))
    assert scaled(root, 100) == expected


@skip_if_no_tk
def test_fit_to_workarea_clamps_to_screen(tk_session_root):
    from config.ui_geometry import fit_to_workarea

    root = tk_session_root
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = fit_to_workarea(root, 10000, 10000)
    assert w <= int(sw * 0.98)
    assert h <= sh - 48


@skip_if_no_tk
def test_fit_to_workarea_keeps_small_values(tk_session_root):
    from config.ui_geometry import fit_to_workarea, scaled

    root = tk_session_root
    w, h = fit_to_workarea(root, scaled(root, 820), scaled(root, 560))
    assert w == scaled(root, 820)
    assert h == scaled(root, 560)


@skip_if_no_tk
def test_centered_geometry_within_parent(tk_session_root):
    """居中坐标落在父窗口范围附近且不为负。"""
    from tkinter import Toplevel

    from config.ui_geometry import centered_geometry, scaled

    top = Toplevel(tk_session_root)
    top.geometry("800x600+100+80")
    top.update_idletasks()
    geo = centered_geometry(top, scaled(top, 400), scaled(top, 300))
    m = re.fullmatch(r"(\d+)x(\d+)\+(\d+)\+(\d+)", geo)
    assert m, geo
    w, h, x, y = (int(v) for v in m.groups())
    assert (w, h) == (scaled(top, 400), scaled(top, 300))
    assert x >= 0 and y >= 0
    # 窗口宽于子窗时，子窗应近似水平居中（±4px 对齐误差）
    if top.winfo_width() >= w:
        assert abs((top.winfo_x() + (top.winfo_width() - w) // 2) - x) <= 4
    top.destroy()
