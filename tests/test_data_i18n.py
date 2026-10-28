"""模板/词库数据双语测试（DATA-I18N-001）。

持久化键保持中文（历史配置与自定义词库 JSON 引用它）；
英文语言下展示名/说明/模板元信息切换为英文内容，
positive_template 本就是英文生图提示词，不参与翻译。
"""

import pytest

from config.i18n import set_language
from services.phrase_library import (
    BUILTIN_PHRASES,
    get_phrase_desc,
    phrase_category_display,
)
from services.prompt_assistant import (
    TEMPLATES,
    category_display,
    display_template,
)


@pytest.fixture(autouse=True)
def _restore_lang():
    yield
    set_language("zh-CN")


def test_all_templates_have_en_meta():
    for tid in TEMPLATES:
        en = display_template(tid)  # 默认 zh → 原始
        assert en["name"] == TEMPLATES[tid]["name"]
    set_language("en")
    for tid, t in TEMPLATES.items():
        view = display_template(tid)
        assert view["name"] != t["name"], f"{tid} 缺少英文名称"
        assert view["desc"] != t["desc"], f"{tid} 缺少英文描述"


def test_en_template_view_keeps_english_prompt_intact():
    set_language("en")
    view = display_template("xhs_hot")
    assert view["positive_template"] == TEMPLATES["xhs_hot"]["positive_template"]


def test_category_display_switches_by_language():
    assert category_display("小红书") == "小红书"
    set_language("en")
    assert category_display("小红书") == "Xiaohongshu"


def test_phrase_category_display_switches_by_language():
    assert phrase_category_display("✨ 画质增强") == "✨ 画质增强"
    set_language("en")
    assert phrase_category_display("✨ 画质增强") == "✨ Quality Boost"
    # 持久化键不被本地化改写
    assert list(BUILTIN_PHRASES.keys())[0] == "✨ 画质增强"


def test_phrase_desc_switches_by_language():
    zh = get_phrase_desc("masterpiece")
    assert "最高画质" in zh
    set_language("en")
    en = get_phrase_desc("masterpiece")
    assert "museum-grade" in en
