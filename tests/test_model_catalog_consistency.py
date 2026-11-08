"""模型目录单一真相护栏：model_catalog ↔ settings 默认值 ↔ provider 兜底 ↔ 向导下拉。

背景：模型 ID/默认值散落在 catalog、settings、provider 的 cfg.get fallback、
向导下拉 values 四处，历史上已发生多次漂移（下拉提供 provider 不认的模型、
默认值停在已下线 ID）。本测试把四方锁进一致——新增/改名模型时必须同步。

与 test_registry_consistency.py（provider 注册表层）互补：这里管「模型族内」。
"""

import ast
import importlib

from config.model_catalog import (
    ARK_IMAGE_DEFAULT,
    ARK_IMAGE_MODELS,
    ARK_IMAGE_NAMES,
    BFL_IMAGE_NAMES,
    BFL_TXT2IMG_DEFAULT,
    BFL_TXT2IMG_MODELS,
    DASHSCOPE_DEFAULT,
    DASHSCOPE_MODELS,
    DASHSCOPE_NAMES,
    GEMINI_IMAGE_DEFAULT,
    GEMINI_IMAGE_MODELS,
    GEMINI_IMAGE_NAMES,
    GEMINI_NB_PRO,
    GPT_IMAGE_DEFAULT,
    GPT_IMAGE_MODELS,
    GPT_IMAGE_NAMES,
    MINIMAX_IMAGE_DEFAULT,
    MINIMAX_IMAGE_MODELS,
    MINIMAX_IMAGE_NAMES,
    RECRAFT_DEFAULT,
    RECRAFT_IMAGE_NAMES,
    RECRAFT_MODELS,
    XAI_IMAGE_DEFAULT,
    XAI_IMAGE_MODELS,
    XAI_IMAGE_NAMES,
)
from config.settings import DEFAULT_CONFIG

_FAMILIES = {
    "gpt_image": (GPT_IMAGE_MODELS, GPT_IMAGE_DEFAULT, GPT_IMAGE_NAMES),
    "gemini_image": (GEMINI_IMAGE_MODELS, GEMINI_IMAGE_DEFAULT, GEMINI_IMAGE_NAMES),
    "minimax_image": (MINIMAX_IMAGE_MODELS, MINIMAX_IMAGE_DEFAULT, MINIMAX_IMAGE_NAMES),
    "ark_image": (ARK_IMAGE_MODELS, ARK_IMAGE_DEFAULT, ARK_IMAGE_NAMES),
    "bfl_txt2img": (BFL_TXT2IMG_MODELS, BFL_TXT2IMG_DEFAULT, BFL_IMAGE_NAMES),
    "xai_image": (XAI_IMAGE_MODELS, XAI_IMAGE_DEFAULT, XAI_IMAGE_NAMES),
    "dashscope": (DASHSCOPE_MODELS, DASHSCOPE_DEFAULT, DASHSCOPE_NAMES),
    "recraft": (RECRAFT_MODELS, RECRAFT_DEFAULT, RECRAFT_IMAGE_NAMES),
}


def test_defaults_are_members_of_their_family():
    """每族默认值必须是本族可选值的一员（默认指向不存在的 ID 是最危险的漂移）。"""
    for fam, (models, default, _names) in _FAMILIES.items():
        assert default in models, f"{fam}: 默认 {default!r} 不在可选值 {models}"


def test_names_cover_all_models():
    """每族的可读名称映射必须覆盖全部可选值，且无多余条目。"""
    for fam, (models, _default, names) in _FAMILIES.items():
        assert set(names) == set(models), f"{fam}: 名称映射与可选值不一致"


def test_no_duplicate_model_ids():
    for fam, (models, _default, _names) in _FAMILIES.items():
        assert len(models) == len(set(models)), f"{fam}: 可选值存在重复"


def test_settings_defaults_match_catalog():
    """settings.DEFAULT_CONFIG 的模型键必须与目录默认一致。"""
    expected = {
        "gpt_image_model": GPT_IMAGE_DEFAULT,
        "gemini_model": GEMINI_IMAGE_DEFAULT,
        "ark_model": ARK_IMAGE_DEFAULT,
        "bfl_model": BFL_TXT2IMG_DEFAULT,
        "dashscope_model": DASHSCOPE_DEFAULT,
        "xai_model": XAI_IMAGE_DEFAULT,
        "recraft_model": RECRAFT_DEFAULT,
    }
    for key, want in expected.items():
        assert DEFAULT_CONFIG.get(key) == want, f"settings.{key} 与目录默认漂移"


def _provider_mod(name: str):
    return importlib.import_module(f"services.providers.{name}")


def test_provider_fallbacks_match_catalog():
    """provider 的 cfg.get 兜底默认必须与目录默认一致（归一化的目标值）。"""
    checks = {
        "openai_image": ("GPT_IMAGE_DEFAULT", GPT_IMAGE_DEFAULT),
        "gemini": ("GEMINI_IMAGE_DEFAULT", GEMINI_IMAGE_DEFAULT),
        "volcengine_ark": ("ARK_IMAGE_DEFAULT", ARK_IMAGE_DEFAULT),
        "bfl_flux": ("BFL_TXT2IMG_DEFAULT", BFL_TXT2IMG_DEFAULT),
        "xai_grok": ("XAI_IMAGE_DEFAULT", XAI_IMAGE_DEFAULT),
        "dashscope_qwen": ("DASHSCOPE_DEFAULT", DASHSCOPE_DEFAULT),
        "minimax_image": ("MINIMAX_IMAGE_DEFAULT", MINIMAX_IMAGE_DEFAULT),
        "recraft": ("RECRAFT_DEFAULT", RECRAFT_DEFAULT),
    }
    for mod_name, (const, want) in checks.items():
        mod = _provider_mod(mod_name)
        got = getattr(mod, const, None)
        assert got == want, f"{mod_name}.{const}={got!r} 与目录默认 {want!r} 漂移"


def test_provider_owned_model_lists_pinned():
    """provider 自有模型清单与 settings 默认值互相锁定（防双份字面量漂移）。"""
    replicate = _provider_mod("replicate_flux")
    assert set(replicate.MODEL_ORDER) == set(replicate._MODELS)
    assert DEFAULT_CONFIG["replicate_model"] in replicate._MODELS
    assert DEFAULT_CONFIG["replicate_model"] == replicate.MODEL_ORDER[0]
    assert set(replicate.REPLICATE_IMAGE_NAMES) == set(replicate._MODELS)

    openrouter = _provider_mod("openrouter")
    assert DEFAULT_CONFIG["openrouter_model"] == openrouter._DEFAULT_MODEL

    # Nano Banana Pro 独立 provider 的固定模型与目录值锁定
    gemini_pro = _provider_mod("gemini_nano_banana_pro")
    assert gemini_pro._MODEL == GEMINI_NB_PRO


def test_provider_memberships_match_catalog():
    """provider 的归一化白名单必须与目录可选值一致。"""
    assert set(_provider_mod("openai_image").GPT_IMAGE_MODELS) == set(GPT_IMAGE_MODELS)
    assert set(_provider_mod("gemini").GEMINI_IMAGE_MODELS) == set(GEMINI_IMAGE_MODELS)
    assert set(_provider_mod("volcengine_ark").ARK_IMAGE_MODELS) == set(ARK_IMAGE_MODELS)
    assert set(_provider_mod("xai_grok").XAI_IMAGE_MODELS) == set(XAI_IMAGE_MODELS)
    assert set(_provider_mod("dashscope_qwen").DASHSCOPE_MODELS) == set(DASHSCOPE_MODELS)


def test_wizard_dropdowns_source_catalog():
    """向导下拉的 values 必须来自目录/注册表，不允许手写字符串清单。"""
    from pathlib import Path

    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    wizard_src = (ui_dir / "wizard_paid.py").read_text(encoding="utf-8")
    free_src = (ui_dir / "wizard_free.py").read_text(encoding="utf-8")

    # Gemini 下拉消费 GEMINI_IMAGE_NAMES（含弃用期限标签）
    assert "values=list(GEMINI_IMAGE_NAMES.values())" in free_src
    # GPT 下拉消费 GPT_IMAGE_NAMES
    assert "values=list(GPT_IMAGE_NAMES.values())" in wizard_src
    # ARK 下拉消费 ARK_IMAGE_NAMES
    assert "values=[ARK_IMAGE_NAMES.get(m, m) for m in ARK_IMAGE_MODELS]" in wizard_src
    # BFL 下拉消费 BFL_IMAGE_NAMES
    assert "values=list(BFL_IMAGE_NAMES.values())" in wizard_src
    # Replicate 下拉消费 provider 的 MODEL_ORDER + REPLICATE_IMAGE_NAMES
    assert "REPLICATE_IMAGE_NAMES.get(m, m) for m in REPLICATE_MODEL_ORDER" in wizard_src


def test_retired_model_ids_absent_from_wizards():
    """已退役/不存在的模型 ID 不得以字符串字面量出现在向导源码（AST 级，
    注释里的提及不受限）。"""
    import re
    from pathlib import Path

    RETIRED = {
        "flux-schnell",
        "flux-kontext-pro",
        "gpt-image-1",
        "gpt-image-1-mini",
        "gpt-image-1.5",
        "doubao-seedream-4-0-t2i",
        "grok-imagine-image-quality",
        "gemini-2.5-flash-image-preview",
    }
    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    for name in ("wizard_paid.py", "wizard_free.py"):
        tree = ast.parse((ui_dir / name).read_text(encoding="utf-8"))
        literals = {
            node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        hits = sorted(literals & RETIRED)
        assert not hits, f"{name} 出现已退役模型 ID 字面量: {hits}"

    # 兜底：形如 provider/model 的 slug 字面量必须属于在册家族
    known_slugs = set()
    for models, *_ in _FAMILIES.values():
        known_slugs.update(m for m in models if "/" in m)
    known_slugs.update(
        _provider_mod("openrouter")._DEFAULT_MODEL,
    )
    for name in ("wizard_paid.py", "wizard_free.py"):
        tree = ast.parse((ui_dir / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if re.fullmatch(r"[a-z0-9_-]+/[a-z0-9._-]+", node.value) and node.value not in known_slugs:
                    raise AssertionError(f"{name} 出现不在册的 slug 字面量: {node.value}")


def test_replicate_dropdown_order_matches_provider_registry():
    """Replicate 下拉顺序与 provider _MODELS 完全一致（防双向漂移）。"""
    mod = _provider_mod("replicate_flux")
    assert set(mod.MODEL_ORDER) == set(mod._MODELS)
    assert mod.MODEL_ORDER[0] == "flux-2-pro"
    assert DEFAULT_CONFIG["replicate_model"] in mod._MODELS
    assert DEFAULT_CONFIG["replicate_model"] == mod.MODEL_ORDER[0]


def test_minimax_family_single_model():
    """MiniMax 官方在册仅 image-01（2026-11 核实），防止臆测性新增。"""
    assert MINIMAX_IMAGE_MODELS == ["image-01"]
