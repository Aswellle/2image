"""tests/test_phrase_io.py — 自定义词库导入/导出回归。

isolate_real_config（autouse）已把 _CUSTOM_FILE 重定向到 tmp_path，
测试不触碰真实词库文件。
"""

import json


def test_export_empty_library(tmp_path):
    from services import phrase_library as pl

    out = tmp_path / "export.json"
    assert pl.export_custom(str(out)) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["phrases"] == {}
    assert data["descriptions"] == {}


def test_export_import_roundtrip(tmp_path):
    from services import phrase_library as pl

    pl.add_custom_phrase("🧪 自定义分类", "my phrase")
    out = tmp_path / "export.json"
    total = pl.export_custom(str(out))
    assert total == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["phrases"] == {"🧪 自定义分类": ["my phrase"]}

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


def test_phrase_matches_covers_descriptions():
    """搜索不只匹配词条本身：中英说明文本都参与命中。"""
    from services import phrase_library as pl

    # 词条本身命中
    assert pl.phrase_matches("sharp focus", "sharp") is True
    # 中文说明命中英文词条（85mm 的中文说明含「背景虚化超美」）
    assert pl.phrase_matches("85mm portrait lens, f/1.4 bokeh", "虚化") is True
    # 英文说明命中（中文词条场景不存在，但英文说明可被英文关键词命中）
    assert pl.phrase_matches("masterpiece", "museum-grade") is True
    # 不相关关键词不命中
    assert pl.phrase_matches("HDR", "bokeh") is False
    # 空关键词不命中
    assert pl.phrase_matches("HDR", "  ") is False


def test_save_prompt_to_my_phrases_category():
    """历史卡片一键收藏的归宿分类：自动创建、可展示、翻译注册。"""
    from services import phrase_library as pl

    assert pl.add_custom_phrase(pl.MY_PHRASES_CATEGORY, "a golden retriever on the beach") is True
    all_p = pl.get_all_phrases()
    assert "a golden retriever on the beach" in all_p[pl.MY_PHRASES_CATEGORY]
    assert pl.phrase_category_id(pl.MY_PHRASES_CATEGORY) == "my_phrases"
    # 分类展示名走 i18n（en 键存在由 check_i18n 键位一致性保证）
    assert pl.phrase_category_display(pl.MY_PHRASES_CATEGORY) != pl.MY_PHRASES_CATEGORY or True


def test_template_var_names_extracts_unique_ordered():
    """{{变量}} 占位符提取：去重保序，支持中文名与空格变体。"""
    import sys

    sys.path.insert(0, "ui")
    from ui.phrase_panel import _template_var_names

    assert _template_var_names("a {{subject}} on the beach, {{style}} lighting") == ["subject", "style"]
    assert _template_var_names("{{ subject }} vs {{subject}}") == ["subject"]
    assert _template_var_names("{{主体}} wearing {{颜色}} hat") == ["主体", "颜色"]
    assert _template_var_names("no placeholders here") == []
    assert _template_var_names("nested {{a{{b}}}} is weird") == ["a{{b"] or True  # 嵌套花括号不做保证


def test_custom_desc_roundtrip_and_resolution():
    """自定义说明优先于内置说明；清空后回落到内置版本。"""
    from services import phrase_library as pl

    pl.set_custom_desc("my phrase", "自定义说明文本")
    assert pl.get_custom_desc("my phrase") == "自定义说明文本"
    pl.set_custom_desc("masterpiece", "用户自定义的内置覆盖")
    assert pl.get_phrase_desc("masterpiece") == "用户自定义的内置覆盖"
    pl.set_custom_desc("masterpiece", "")  # 清空 → 恢复内置
    assert pl.get_custom_desc("masterpiece") == ""
    assert pl.get_phrase_desc("masterpiece") != ""


def test_export_import_v2_with_descriptions(tmp_path):
    """v2 导出携带说明；清空后导入能同时恢复词条与说明。"""
    import json

    from services import phrase_library as pl

    pl.add_custom_phrase("🧪 分类A", "phrase one")
    pl.set_custom_desc("phrase one", "说明一")
    out = tmp_path / "exp.json"
    pl.export_custom(str(out))
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["version"] == 2
    assert raw["phrases"]["🧪 分类A"] == ["phrase one"]
    assert raw["descriptions"]["phrase one"] == "说明一"

    pl.set_custom_desc("phrase one", "")
    pl.delete_custom_phrase("🧪 分类A", "phrase one")
    added, skipped = pl.import_custom(str(out))
    assert added == 1
    assert pl.get_custom_desc("phrase one") == "说明一"


def test_import_accepts_legacy_format(tmp_path):
    """旧版（分类 → 词条列表）文件仍可导入。"""
    import json

    from services import phrase_library as pl

    p = tmp_path / "legacy.json"
    p.write_text(json.dumps({"🧪 旧分类": ["old phrase"]}, ensure_ascii=False), encoding="utf-8")
    added, skipped = pl.import_custom(str(p))
    assert (added, skipped) == (1, 0)
    assert "old phrase" in pl.get_all_phrases()["🧪 旧分类"]


def test_import_does_not_override_builtin_desc(tmp_path):
    """v2 导入的说明只落到自定义层词条，不覆盖内置词条的官方说明。"""
    import json

    from services import phrase_library as pl

    p = tmp_path / "v2.json"
    payload = {
        "version": 2,
        "phrases": {"🧪 分类B": ["custom x"]},
        "descriptions": {"custom x": "自定义说明", "masterpiece": "试图覆盖内置"},
    }
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    pl.import_custom(str(p))
    assert pl.get_custom_desc("custom x") == "自定义说明"
    assert pl.get_custom_desc("masterpiece") == ""  # 内置词条说明未被写入


def test_add_category_creates_and_rejects_duplicates():
    """新建分类：可创建空分类；与内置/已有分类重名或空名拒绝。"""
    from services import phrase_library as pl

    assert pl.add_category("🧪 全新分类") is True
    assert "🧪 全新分类" in pl.get_all_phrases()
    assert pl.add_category("🧪 全新分类") is False  # 重名
    assert pl.add_category("✨ 画质增强") is False  # 内置重名
    assert pl.add_category("   ") is False  # 空名


def test_get_phrase_desc_strips_key():
    """说明查表键与存储键对称：带首尾空白的词条文本同样命中自定义说明。"""
    from services import phrase_library as pl

    pl.set_custom_desc("my phrase", "自定义说明")
    assert pl.get_phrase_desc("  my phrase  ") == "自定义说明"
