"""Tests for image_service provider fallback."""
import pytest
from services.image_service import generate_image


def test_all_providers_fail_raises_runtimeerror():
    """When all providers fail, generate_image should raise RuntimeError."""
    cfg = {}  # no keys configured
    # Only use providers that require API keys (they will raise ValueError)
    key_required = [
        "Google Gemini (免费500次/天)",
        "硅基流动 SiliconFlow (★推荐)",
        "OpenRouter (部分免费)",
    ]
    with pytest.raises(RuntimeError, match="所有接口均失败"):
        generate_image("test prompt", 512, 512, 42, cfg, provider_order=key_required)


def test_runtimeerror_triggers_provider_fallback():
    """RuntimeError from a provider must fall through to the next provider."""
    from unittest.mock import patch

    def bad_provider(prompt, w, h, seed, cfg, log):
        raise RuntimeError("Blocked unsafe image URL: https://10.0.0.1/evil.png")

    def good_provider(prompt, w, h, seed, cfg, log):
        return b"fake_image_bytes", "GoodProvider"

    with patch("services.image_service.ALL_PROVIDERS",
               {"bad": bad_provider, "good": good_provider}):
        data, used = generate_image("test", 512, 512, 42, {},
                                    provider_order=["bad", "good"])
    assert used == "GoodProvider"
    assert data == b"fake_image_bytes"


def test_timeouterror_triggers_provider_fallback():
    """TimeoutError from a provider must fall through to the next provider."""
    from unittest.mock import patch

    def timeout_provider(prompt, w, h, seed, cfg, log):
        raise TimeoutError("120s timeout waiting for response")

    def good_provider(prompt, w, h, seed, cfg, log):
        return b"image_bytes", "GoodProvider"

    with patch("services.image_service.ALL_PROVIDERS",
               {"slow": timeout_provider, "good": good_provider}):
        data, used = generate_image("test", 512, 512, 42, {},
                                    provider_order=["slow", "good"])
    assert used == "GoodProvider"


def test_save_image_file():
    """save_image_file should create a valid PNG with metadata."""
    from services.image_service import save_image_file
    from PIL import Image
    import io, os

    # Create a tiny test image
    img = Image.new('RGB', (64, 64), color='blue')
    buf = io.BytesIO()
    img.save(buf, 'PNG')

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
