"""tests/test_phrase_io.py — 自定义词库导入/导出回归。

isolate_real_config（autouse）已把 _CUSTOM_FILE 重定向到 tmp_path，
测试不触碰真实词库文件。
"""

import json


def test_export_empty_library(tmp_path):
    from services import phrase_library as pl

    out = tmp_path / "export.json"
    assert pl.export_custom(str(out)) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == {}


def test_export_import_roundtrip(tmp_path):
    from services import phrase_library as pl

    pl.add_custom_phrase("🧪 自定义分类", "my phrase")
    out = tmp_path / "export.json"
    total = pl.export_custom(str(out))
    assert total == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data == {"🧪 自定义分类": ["my phrase"]}

    # 导入同一文件：全部已存在 → 跳过
    added, skipped = pl.import_custom(str(out))
    assert (added, skipped) == (0, 1)


def test_import_merges_and_skips_builtin(tmp_path):
    from services import phrase_library as pl

    src = tmp_path / "in.json"
    src.write_text(
        json.dumps(
            {
                "✨ 画质增强": ["masterpiece", "brand new booster"],  # 内置词条跳过
                "🧪 自定义分类": ["", "  ", "another phrase"],  # 空词条跳过
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    added, skipped = pl.import_custom(str(src))
    assert added == 2
    assert skipped == 3
    all_phrases = pl.get_all_phrases()
    assert "brand new booster" in all_phrases["✨ 画质增强"]
    assert "another phrase" in all_phrases["🧪 自定义分类"]


def test_import_rejects_invalid_structure(tmp_path):
    from services import phrase_library as pl

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    try:
        pl.import_custom(str(bad))
        raise AssertionError("expected ValueError for invalid structure")
    except ValueError:
        pass


def test_record_phrase_use_counts_and_persists():
    from services import phrase_library as pl

    pl.record_phrase_use("masterpiece")
    pl.record_phrase_use("masterpiece")
    pl.record_phrase_use("golden hour lighting")
    usage = pl.get_phrase_usage()
    assert usage["masterpiece"] == 2
    assert usage["golden hour lighting"] == 1

    # 文件真实落盘（重载后仍在）
    pl2_usage = pl._load_usage()
    assert pl2_usage == usage


def test_record_phrase_use_ignores_blank():
    from services import phrase_library as pl

    pl.record_phrase_use("   ")
    assert pl.get_phrase_usage() == {}


def test_usage_sort_order_in_panel_reload():
    """高频词条应排在分类列表前面（稳定排序，同频保持原序）。"""
    from services import phrase_library as pl

    for _ in range(3):
        pl.record_phrase_use("best quality")
    pl.record_phrase_use("HDR")
    all_phrases = pl.get_all_phrases()
    items = all_phrases["✨ 画质增强"]
    usage = pl.get_phrase_usage()
    ranked = sorted(items, key=lambda phrase: -usage.get(phrase, 0))
    assert ranked[:2] == ["best quality", "HDR"]


def test_add_custom_phrase_duplicate_reports_false():
    """重复词条（自定义或内置）不写入并返回 False，供 UI 给出去重反馈。"""
    from services import phrase_library as pl

    assert pl.add_custom_phrase("✨ 画质增强", "my test phrase") is True
    assert pl.add_custom_phrase("✨ 画质增强", "my test phrase") is False
    # 与内置词条同分类重复 → 不写入自定义层
    assert pl.add_custom_phrase("✨ 画质增强", "masterpiece") is False
    data = pl._load_custom()
    assert data["✨ 画质增强"] == ["my test phrase"]
    # 空白词条直接拒绝
    assert pl.add_custom_phrase("✨ 画质增强", "   ") is False
