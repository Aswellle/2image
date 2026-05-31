"""Tests for provider error handling."""
import pytest


def test_gemini_missing_key_raises_valueerror():
    from services.providers.gemini import try_gemini
    with pytest.raises(ValueError, match="API Key"):
        try_gemini("test prompt", 512, 512, 42, {"gemini_key": ""}, print)


def test_openai_dalle_missing_key_raises_valueerror():
    from services.providers.openai_dalle import try_openai_dalle
    with pytest.raises(ValueError, match="API Key"):
        try_openai_dalle("test prompt", 1024, 1024, 42, {"openai_key": ""}, print)


def test_siliconflow_missing_key_raises_valueerror():
    from services.providers.siliconflow import try_siliconflow
    with pytest.raises(ValueError, match="API Key"):
        try_siliconflow("test prompt", 512, 512, 42, {"sf_key": ""}, print)


def test_validate_image_url_blocks_internal():
    from services.providers.siliconflow import _validate_image_url
    assert not _validate_image_url("http://127.0.0.1/test.png")
    assert not _validate_image_url("http://10.0.0.1/test.png")
    assert not _validate_image_url("http://192.168.1.1/test.png")
    assert _validate_image_url("https://cdn.example.com/test.png")
