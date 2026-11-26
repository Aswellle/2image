"""Tests for image_service provider fallback."""

import pytest
from services.image_service import generate_image


def test_all_providers_fail_raises_typed_final_error():
    """全链失败时重抛编排器的最后一个类型化错误（弹窗门控生产可达）。

    三家需 Key 的接口在空配置下全部 ProviderConfigError——generate_image
    应重抛 final_error（带 .provider 与 .next_step），而非裸 RuntimeError。
    仅保留这三家，避免兜底追加真正的免 Key 接口而触发网络请求。
    """
    from unittest.mock import patch

    from services.generation.errors import ProviderConfigError
    from services.providers import ALL_PROVIDERS as REAL_PROVIDERS

    key_required = ["gemini", "siliconflow", "openrouter"]  # registry stable ids
    subset = {name: REAL_PROVIDERS[name] for name in key_required}
    with patch("services.image_service.ALL_PROVIDERS", subset):
        with pytest.raises(ProviderConfigError) as ei:
            generate_image("test prompt", 512, 512, 42, {}, provider_order=key_required)
    assert ei.value.provider in key_required  # 编排器兜底填充来源
    assert ei.value.next_step  # 弹窗门控与指引可用


def test_runtimeerror_triggers_provider_fallback():
    """RuntimeError from a provider must fall through to the next provider."""
    from unittest.mock import patch

    def bad_provider(prompt, w, h, seed, cfg, log):
        raise RuntimeError("Blocked unsafe image URL: https://10.0.0.1/evil.png")

    def good_provider(prompt, w, h, seed, cfg, log):
        return b"fake_image_bytes", "GoodProvider"

    with patch("services.image_service.ALL_PROVIDERS", {"bad": bad_provider, "good": good_provider}):
        data, used = generate_image("test", 512, 512, 42, {}, provider_order=["bad", "good"])
    assert used == "GoodProvider"
    assert data == b"fake_image_bytes"


def test_timeouterror_triggers_provider_fallback():
    """TimeoutError from a provider must fall through to the next provider."""
    from unittest.mock import patch

    def timeout_provider(prompt, w, h, seed, cfg, log):
        raise TimeoutError("120s timeout waiting for response")

    def good_provider(prompt, w, h, seed, cfg, log):
        return b"image_bytes", "GoodProvider"

    with patch("services.image_service.ALL_PROVIDERS", {"slow": timeout_provider, "good": good_provider}):
        data, used = generate_image("test", 512, 512, 42, {}, provider_order=["slow", "good"])
    assert used == "GoodProvider"


def test_save_image_file():
    """save_image_file should create a valid PNG with metadata."""
    from services.image_service import save_image_file
    from PIL import Image
    import io, os

    # Create a tiny test image
    img = Image.new("RGB", (64, 64), color="blue")
    buf = io.BytesIO()
    img.save(buf, "PNG")

    path = save_image_file(buf.getvalue(), "test prompt", seed=42, provider="Test", size="64x64")
    try:
        assert os.path.exists(path)
        loaded = Image.open(path)
        try:
            assert loaded.info.get("Prompt") == "test prompt"
            assert loaded.info.get("Seed") == "42"
            assert loaded.info.get("Provider") == "Test"
        finally:
            loaded.close()
    finally:
        os.unlink(path)


def _patch_registry(providers: dict, free: set, img2img: set | None = None):
    """Patch the registry views consumed inside generate_image()."""
    from unittest.mock import patch

    return [
        patch("services.image_service.ALL_PROVIDERS", providers),
        patch("services.providers.FREE_PROVIDERS", free),
        patch("services.providers.PROVIDER_KEYS", {pid: None for pid in providers}),
        patch("services.providers.MULTI_KEY_PROVIDERS", {}),
        patch("services.providers.OPTIONAL_KEY_PROVIDERS", set()),
        patch("services.providers.IMG2IMG_PROVIDERS", img2img or {}),
    ]


def test_appended_provider_is_used_as_fallback():
    """显式顺序之外的可用接口必须真正参与兜底（追加到 orchestrator 顺序）。"""

    def bad_provider(prompt, w, h, seed, cfg, log):
        raise RuntimeError("provider failed")

    def good_provider(prompt, w, h, seed, cfg, log):
        return b"fallback-image", "Good"

    providers = {"bad": bad_provider, "good": good_provider}
    patches = _patch_registry(providers, {"bad", "good"})
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        data, used = generate_image("test", 512, 512, 42, {}, provider_order=["bad"])
    assert data == b"fallback-image"
    assert used == "Good"


def test_img2img_fallback_skips_text_only_providers():
    """图生图兜底只能追加支持参考图的接口，避免参考图被静默忽略。"""
    calls: list[str] = []

    def bad_i2i(prompt, w, h, seed, cfg, log):
        calls.append("bad_i2i")
        raise RuntimeError("provider failed")

    def t2i_only(prompt, w, h, seed, cfg, log):
        calls.append("t2i_only")
        return b"text-only", "T2I"

    def good_i2i(prompt, w, h, seed, cfg, log):
        calls.append("good_i2i")
        return b"i2i-image", "GoodI2I"

    providers = {"bad_i2i": bad_i2i, "t2i_only": t2i_only, "good_i2i": good_i2i}
    patches = _patch_registry(providers, set(providers), {"bad_i2i", "good_i2i"})
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        data, used = generate_image(
            "edit this", 512, 512, 42, {}, provider_order=["bad_i2i"], ref_image=b"\x89PNG-fake"
        )
    assert data == b"i2i-image"
    assert used == "GoodI2I"
    assert "t2i_only" not in calls


def test_disabled_pollinations_is_not_appended_as_fallback():
    calls: list[str] = []

    def bad_provider(prompt, w, h, seed, cfg, log):
        calls.append("bad")
        raise RuntimeError("provider failed")

    def pollinations_provider(prompt, w, h, seed, cfg, log):
        calls.append("pollinations")
        return b"image", "Pollinations"

    providers = {"bad": bad_provider, "pollinations": pollinations_provider}
    patches = _patch_registry(providers, set(providers))
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        with pytest.raises(Exception):
            generate_image("test", 512, 512, 42, {"pollinations_enabled": False}, provider_order=["bad"])
    assert "pollinations" not in calls
