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
