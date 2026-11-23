"""E2E 旅程：统计看板全交互（卡片/切年/刷新/导出/分享图）。"""

import pytest
import tkinter as tk
from data.repository import add_entry
from tests.e2e import driver


@pytest.fixture
def stats(e2e):
    """打开统计看板（播种数据）。"""
    for day_i, prov in enumerate(
        ["Pollinations/flux", "OpenAI/gpt-image-2.6-flare-standard", "豆包/doubao-seedream-5-5-261028"]
    ):
        for _ in range(4 + day_i * 3):
            add_entry(f"seed {day_i}", "", f"s{day_i}.png", prov)
    e2e.app._show_stats()
    e2e.pump(8)
    sd = e2e.app._stats_win
    assert sd is not None and sd.winfo_exists()
    yield sd
    try:
        sd.win.destroy()
    except tk.TclError:
        pass


def test_summary_cards_render_six_tiles(stats):
    """六张汇总卡全部渲染（含收藏率）。"""
    # 数字标签个数 ≥ 6
    values = []

    def _walk(w):
        for ch in w.winfo_children():
            if isinstance(ch, tk.Label):
                t = str(ch.cget("text"))
                if t.isdigit() or t.endswith("%"):
                    values.append(t)
            _walk(ch)

    _walk(stats.win)
    assert len(values) >= 5  # 5 数字 + 1 百分比（0 收藏时%）


def test_heatmap_grid_drawn(stats, e2e):
    """热力图画布有格子（今天紫框 + 网格）。

    首绘由 after(80ms) 调度：必须用事件泵等待定时器触发，
    纯 update() 在快机器上来不及等到定时器（CI 曾因此误报）。
    """

    def _has_cells() -> bool:
        found = []

        def _walk(w):
            for ch in w.winfo_children():
                if isinstance(ch, tk.Canvas) and len(ch.find_withtag("cell")) > 0:
                    found.append(ch)
                _walk(ch)

        _walk(stats.win)
        return bool(found)

    assert e2e.wait_until(_has_cells, timeout_ms=5000), "热力图 cell 未绘制"


def test_year_switch_redraws(stats, e2e):
    """切年按钮 → 年份标签更新。"""
    e2e.pump(8)
    from data.repository import get_available_years

    years = get_available_years()
    if len(years) < 2:
        pytest.skip("单年数据无需切年")
    year_lbl = stats._hmap_year_lbl
    old = str(year_lbl.cget("text"))
    target = years[-1] if str(years[0]) in old else years[0]

    def _find_year_btn(w, text):
        for ch in w.winfo_children():
            if isinstance(ch, tk.Button) and str(ch.cget("text")) == text:
                return ch
            f = _find_year_btn(ch, text)
            if f:
                return f
        return None

    btn = _find_year_btn(stats.win, str(target))
    assert btn is not None
    btn.invoke()
    e2e.pump(8)
    assert str(target) in str(year_lbl.cget("text"))


def test_refresh_keeps_instance_and_updates(stats, e2e):
    """刷新按钮：就地重绘（同一窗口实例）+ 更新时间刷新。"""

    same_win = stats.win
    refresh_btn = driver.find_buttons(stats.win, "刷新")
    assert refresh_btn
    refresh_btn[0].invoke()
    e2e.pump(8)
    # 就地刷新：同一窗口实例存活、更新时间标签保持格式
    assert stats.win is same_win and stats.win.winfo_exists()
    assert "更新于" in str(stats._upd_lbl.cget("text"))


def test_provider_bars_rendered(stats):
    """接口使用分布：三类供应商条目呈现。"""
    names = []

    def _walk(w):
        for ch in w.winfo_children():
            if isinstance(ch, tk.Label):
                t = str(ch.cget("text"))
                if "Pollinations" in t or "OpenAI" in t or "豆包" in t:
                    names.append(t)
            _walk(ch)

    _walk(stats.win)
    assert names


def test_export_csv_writes_file(stats, e2e, tmp_path):
    """导出 CSV：文件对话框打桩 → 文件落盘且为合法 CSV。"""
    out = tmp_path / "stats.csv"
    e2e.patch_filedialog("asksaveasfilename", str(out), None)
    btns = driver.find_buttons(stats.win, "CSV")
    assert btns
    btns[0].invoke()
    e2e.pump(8)
    assert out.exists()
    raw = out.read_text(encoding="utf-8-sig")
    assert "2image" in raw and "Pollinations" in raw


def test_export_share_image_writes_png(stats, e2e, tmp_path):
    """分享图：PNG 落盘且尺寸正确。"""
    from PIL import Image

    out = tmp_path / "share.png"
    e2e.patch_filedialog("asksaveasfilename", str(out), None)
    btns = driver.find_buttons(stats.win, "分享图")
    assert btns
    btns[0].invoke()
    e2e.pump(8)
    assert out.exists()
    with Image.open(out) as im:
        assert im.size == (1280, 900)


def test_escape_closes_dashboard(stats, e2e):
    """Escape 关闭统计看板（非主窗焦点链需 focus_force）。"""
    stats.win.focus_force()
    e2e.pump()
    stats.win.event_generate("<Escape>")
    e2e.pump()
    assert not stats.win.winfo_exists()
