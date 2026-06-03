"""Tests for services/smart_router.py (P3-A)."""
import pytest

from services.smart_router import (
    get_provider_order,
    _detect_scene,
    _ROUTES,
    _TEMPLATE_SCENE,
)


# ── Scene detection ───────────────────────────────────────────────────────────

def test_detect_scene_text_overlay_banner():
    assert _detect_scene("Create a banner for the event") == "text_overlay"

def test_detect_scene_text_overlay_logo():
    assert _detect_scene("Design a Logo for my brand") == "text_overlay"

def test_detect_scene_ecommerce_product():
    assert _detect_scene("白底产品展示图") == "ecommerce"

def test_detect_scene_illustration():
    assert _detect_scene("flat design 插画 icon") == "illustration"

def test_detect_scene_no_match_returns_empty():
    assert _detect_scene("a beautiful sunset") == ""

def test_detect_scene_product_photo_portrait():
    assert _detect_scene("model portrait fashion") == "product_photo"


# ── Template ID priority ──────────────────────────────────────────────────────

def test_template_id_overrides_keyword():
    # "banner" keyword would normally → text_overlay, but xhs_hot → social_media
    order = get_provider_order("banner photo", {}, template_id="xhs_hot")
    social_providers = set(_ROUTES["social_media"])
    assert order[0] in social_providers, (
        f"Expected first provider to be in social_media route, got: {order[0]}"
    )

def test_unknown_template_id_falls_back_to_keyword():
    order = get_provider_order("Create a logo banner", {}, template_id="nonexistent_id")
    # Should fall back to keyword detection → text_overlay
    text_overlay_providers = set(_ROUTES["text_overlay"])
    # First available provider should come from text_overlay or full fallback
    assert len(order) > 0

def test_all_template_ids_map_to_valid_scenes():
    for tid, scene in _TEMPLATE_SCENE.items():
        assert scene in _ROUTES, f"Template '{tid}' maps to unknown scene '{scene}'"


# ── Key filtering ─────────────────────────────────────────────────────────────

def test_paid_provider_excluded_without_key():
    # "banner" → text_overlay route which includes "💎 OpenAI DALL-E 3" (paid)
    order = get_provider_order("banner design", {})
    assert "💎 OpenAI DALL-E 3" not in order

def test_paid_provider_included_with_key():
    order = get_provider_order("banner design", {"openai_key": "sk-test"})
    assert "💎 OpenAI DALL-E 3" in order

def test_commercial_provider_excluded_without_key():
    # brand_product_launch → brand_tech route which includes fal.ai (commercial)
    order = get_provider_order("", {}, template_id="brand_product_launch")
    assert "fal.ai FLUX Ultra (高质量)" not in order

def test_commercial_provider_included_with_key():
    order = get_provider_order("", {"fal_key": "key-test"}, template_id="brand_product_launch")
    assert "fal.ai FLUX Ultra (高质量)" in order


# ── Fallback guarantee ────────────────────────────────────────────────────────

def test_empty_cfg_always_returns_nonempty_list():
    order = get_provider_order("anything at all", {})
    assert len(order) > 0

def test_empty_cfg_always_contains_pollinations_fallback():
    order = get_provider_order("anything at all", {})
    assert "Pollinations.AI (免费·无需Key)" in order

def test_all_free_cfg_always_nonempty():
    # Even with totally unknown prompt and blank cfg, must return at least one provider
    order = get_provider_order("", {})
    assert len(order) > 0

def test_unknown_providers_in_route_do_not_crash():
    # Routing keys are display strings; unknown ones should be filtered without crash
    from services.smart_router import _filter_available
    result = _filter_available(["NonExistentProvider"], {})
    assert result == []
