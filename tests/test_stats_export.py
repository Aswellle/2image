"""tests/test_stats_export.py — 统计导出（CSV/分享图）回归。

isolate_real_config（autouse）已隔离 DB 与台账文件；导出只写用户指定路径。
"""

import csv
import os

import pytest

from data import repository


@pytest.fixture(autouse=True)
def setup_db():
    repository._set_test_db(":memory:")
    repository.init_db()
    yield


def _seed():
    from data import repository

    repository.add_entry("a", "", "/tmp/a.png", "Pollinations/flux")
    repository.add_entry("b", "", "/tmp/b.png", "OpenAI/gpt-image-2.6-flare-standard")
    repository.add_entry("c", "", "/tmp/c.png", "OpenAI/gpt-image-2.6-flare-hd")
    repository.update_tags(1, "夜景, 人像")


def test_build_stats_csv_sections_and_values(tmp_path):
    _seed()
    from services.stats_export import build_stats_csv

    out = tmp_path / "stats.csv"
    n = build_stats_csv(str(out))
    assert n > 0 and out.exists()
    raw = out.read_text(encoding="utf-8-sig")
    assert raw.startswith("2image")  # 品牌行
    with open(out, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    flat = [",".join(r) for r in rows]
    assert any(len(r) == 2 and r[-1] == "3" for r in rows)  # 汇总：总生成 3 张
    assert any("OpenAI/gpt-image-2.6-flare-standard" in r for r in flat)  # 接口分布
    assert any(r[-1] == "0.1" for r in rows if len(r) == 3)  # 成本行：0.05×2=0.1
    assert any("夜景" in r for r in flat)  # 标签


def test_csv_escapes_formula_injection(tmp_path):
    """供应商串/标签以 = + - @ 开头时前置单引号，防表格公式执行。"""
    repository.add_entry("x", "", "/tmp/x.png", '=HYPERLINK("http://evil","x")')
    repository.update_tags(1, "=1+1, +cmd, 正常标签")
    from services.stats_export import build_stats_csv

    out = tmp_path / "inj.csv"
    build_stats_csv(str(out))
    with open(out, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    cells = [r[0] for r in rows if r]
    assert any(c.startswith("'=HYPERLINK") for c in cells)
    assert "'=1+1" in cells
    assert "'+cmd" in cells
    assert "正常标签" in cells


def test_render_share_image_writes_png(tmp_path):
    _seed()
    from PIL import Image

    from services.stats_export import render_share_image

    out = tmp_path / "share.png"
    ret = render_share_image(str(out))
    assert ret == str(out) and out.exists()
    assert os.path.getsize(out) > 10_000
    with Image.open(out) as im:
        assert im.size == (1280, 900)


def test_render_share_image_handles_long_tag_footer(tmp_path):
    """超长标签不得让脚注行溢出画布（按剩余宽度截断后仍能出图）。"""
    from PIL import Image

    from services.stats_export import render_share_image

    repository.add_entry("x", "", "/tmp/x.png", "Pollinations/flux")
    repository.update_tags(1, "一个非常长的标签名称" * 8)
    out = tmp_path / "longtag.png"
    render_share_image(str(out))
    with Image.open(out) as im:
        assert im.size == (1280, 900)


def test_render_share_image_empty_db(tmp_path):
    """空库也能出图：零值卡片 + 无付费条目，不抛异常。"""
    from services.stats_export import render_share_image

    out = tmp_path / "empty.png"
    assert render_share_image(str(out)) == str(out)
    assert out.exists()
