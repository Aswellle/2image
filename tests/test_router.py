"""
tests/test_router.py — Health-aware scoring router tests
─────────────────────────────────────────────────────────
Validates provider manifest resolution, legacy alias mapping,
capability filtering, health-based scoring, and free/paid policy.
"""
from __future__ import annotations

import pytest

from services.generation.provider_health import get_health_registry
from services.generation.provider_manifest import (
    ALL_MANIFESTS,
    FREE_MANIFESTS,
    PAID_MANIFESTS,
    LEGACY_NAME_TO_ID,
    resolve_provider_id,
)
from services.generation.router import Router, get_provider_order


@pytest.fixture(autouse=True)
def reset_health():
    """Reset health registry before each test."""
    reg = get_health_registry()
    reg.reset()
    yield
    reg.reset()


class TestProviderManifest:
    def test_all_manifests_have_unique_ids(self):
        ids = [m.id for m in ALL_MANIFESTS.values()]
        assert len(ids) == len(set(ids))

    def test_free_manifests_count(self):
        assert len(FREE_MANIFESTS) >= 10

    def test_paid_manifests_count(self):
        assert len(PAID_MANIFESTS) >= 5

    def test_manifest_frozen(self):
        m = ALL_MANIFESTS["siliconflow"]
        with pytest.raises(AttributeError):
            m.name = "new name"

    def test_needs_key_property(self):
        m = ALL_MANIFESTS["siliconflow"]
        assert m.needs_key is True
        m_free = ALL_MANIFESTS["pollinations"]
        assert m_free.needs_key is False

    def test_img2img_capability(self):
        m = ALL_MANIFESTS["openai_image"]
        assert m.supports_img2img is True
        assert "img2img" in m.capabilities


class TestLegacyAliases:
    def test_all_legacy_names_resolve(self):
        for legacy_name, expected_id in LEGACY_NAME_TO_ID.items():
            resolved = resolve_provider_id(legacy_name)
            assert resolved == expected_id, f"{legacy_name} → {resolved} (expected {expected_id})"

    def test_id_passes_through(self):
        assert resolve_provider_id("siliconflow") == "siliconflow"
        assert resolve_provider_id("openai_image") == "openai_image"

    def test_unknown_returns_none(self):
        assert resolve_provider_id("nonexistent_provider") is None


class TestRouter:
    def test_free_only_by_default(self):
        cfg = {"sf_key": "xxx", "openai_key": "yyy"}
        router = Router(cfg)
        order = router.get_order()
        # Should only include free providers
        for pid in order:
            assert pid in FREE_MANIFESTS, f"{pid} is not free"

    def test_paid_included_with_preference(self):
        cfg = {"sf_key": "xxx", "openai_key": "yyy"}
        router = Router(cfg)
        order = router.get_order(prefer_paid=True)
        # Should include paid providers
        has_paid = any(pid in PAID_MANIFESTS for pid in order)
        assert has_paid

    def test_explicit_provider(self):
        cfg = {"sf_key": "xxx"}
        router = Router(cfg)
        order = router.get_order(explicit_provider="siliconflow")
        assert order == ["siliconflow"]

    def test_explicit_legacy_name(self):
        cfg = {"sf_key": "xxx"}
        router = Router(cfg)
        order = router.get_order(explicit_provider="硅基流动 SiliconFlow (★推荐)")
        assert order == ["siliconflow"]

    def test_img2img_filter(self):
        cfg = {"sf_key": "xxx", "openai_key": "yyy"}
        router = Router(cfg)
        order = router.get_order(prefer_paid=True, require_img2img=True)
        for pid in order:
            m = ALL_MANIFESTS[pid]
            assert m.supports_img2img, f"{pid} doesn't support img2img"

    def test_missing_key_excluded(self):
        cfg = {}  # No keys configured
        router = Router(cfg)
        order = router.get_order()
        for pid in order:
            m = ALL_MANIFESTS[pid]
            if m.config_key:
                assert cfg.get(m.config_key), f"{pid} needs key but not configured"

    def test_always_has_fallback(self):
        cfg = {}
        router = Router(cfg)
        order = router.get_order()
        assert "pollinations" in order

    def test_unhealthy_provider_scored_lower(self):
        reg = get_health_registry()
        # Make siliconflow unhealthy
        health = reg.get("siliconflow")
        for _ in range(health.OPEN_THRESHOLD):
            health.record_failure("transient")

        cfg = {"sf_key": "xxx"}
        router = Router(cfg)
        order = router.get_order()

        # Unhealthy provider should be ranked lower
        sf_idx = order.index("siliconflow") if "siliconflow" in order else -1
        poll_idx = order.index("pollinations")
        if sf_idx >= 0:
            assert sf_idx > poll_idx, "Unhealthy provider should rank below healthy ones"

    def test_empty_cfg_still_returns_order(self):
        cfg = {}
        router = Router(cfg)
        order = router.get_order()
        assert len(order) > 0


class TestGetProviderOrder:
    def test_convenience_function(self):
        cfg = {"sf_key": "xxx"}
        order = get_provider_order(prompt="test", cfg=cfg)
        assert isinstance(order, list)
        assert len(order) > 0

    def test_convenience_with_paid(self):
        cfg = {"sf_key": "xxx", "openai_key": "yyy"}
        order = get_provider_order(prompt="test", cfg=cfg, prefer_paid=True)
        has_paid = any(pid in PAID_MANIFESTS for pid in order)
        assert has_paid
