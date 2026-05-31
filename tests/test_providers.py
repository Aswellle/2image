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


import importlib

# Parametrized: all providers that require a non-empty API key must raise ValueError
# when that key is absent. This enforces the provider error-contract.
# stablehorde is excluded: empty key = anonymous mode (valid usage).
_PROVIDER_KEY_CASES = [
    ("services.providers.huggingface",   "try_hf_inference",  {"hf_token": ""}),
    ("services.providers.cloudflare_ai", "try_cloudflare_ai", {"cf_account_id": "", "cf_api_token": ""}),
    ("services.providers.segmind",       "try_segmind",       {"segmind_key": ""}),
    ("services.providers.replicate_flux","try_replicate",     {"replicate_key": ""}),
    ("services.providers.stability_ai",  "try_stability_ai",  {"stability_key": ""}),
    ("services.providers.together_ai",   "try_together_ai",   {"together_key": ""}),
    ("services.providers.xai_grok",      "try_xai_grok",      {"xai_key": ""}),
    ("services.providers.openrouter",    "try_openrouter",    {"openrouter_key": ""}),
    ("services.providers.fal_flux",      "try_fal_flux",      {"fal_key": ""}),
    ("services.providers.ideogram",      "try_ideogram",      {"ideogram_key": ""}),
    ("services.providers.recraft",       "try_recraft",       {"recraft_key": ""}),
    ("services.providers.modelslab",     "try_modelslab",     {"modelslab_key": ""}),
]

@pytest.mark.parametrize("module,fn,cfg", _PROVIDER_KEY_CASES,
                          ids=[c[1] for c in _PROVIDER_KEY_CASES])
def test_provider_missing_key_raises_valueerror(module, fn, cfg):
    """Every keyed provider must raise ValueError on missing/empty API key."""
    mod = importlib.import_module(module)
    func = getattr(mod, fn)
    with pytest.raises(ValueError):
        func("test prompt", 512, 512, 42, cfg, print)


def test_validate_image_url_blocks_non_https():
    from services.providers._net import validate_image_url
    assert not validate_image_url("http://cdn.example.com/test.png")
    assert not validate_image_url("ftp://cdn.example.com/test.png")
    assert not validate_image_url("")


def test_validate_image_url_blocks_literal_private_ips():
    from services.providers._net import validate_image_url
    # These must be blocked regardless of scheme — the CRITICAL test cases
    # (old implementation only blocked these via scheme check on http://, not IP logic)
    assert not validate_image_url("https://127.0.0.1/test.png")        # loopback
    assert not validate_image_url("https://10.0.0.1/test.png")         # RFC1918 private
    assert not validate_image_url("https://192.168.1.1/test.png")      # RFC1918 private
    assert not validate_image_url("https://172.16.0.1/test.png")       # RFC1918 private
    assert not validate_image_url("https://169.254.169.254/latest/")   # link-local / cloud metadata


def test_validate_image_url_blocks_localhost_hostname():
    from services.providers._net import validate_image_url
    # DNS names that resolve to internal IPs must be blocked (was the SSRF hole)
    assert not validate_image_url("https://localhost/test.png")


def test_validate_image_url_unresolvable_is_blocked():
    from services.providers._net import validate_image_url
    # Fail-closed: unresolvable hostnames are rejected, not allowed
    assert not validate_image_url("https://this.host.does.not.exist.invalid/x.png")


def test_validate_image_url_allows_public_cdn():
    from services.providers._net import validate_image_url
    from unittest.mock import patch
    import socket
    # Mock DNS to return a known public IP (1.1.1.1 = Cloudflare) for the CDN hostname
    mock_result = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('1.1.1.1', 443))]
    with patch('services.providers._net.socket.getaddrinfo', return_value=mock_result):
        assert validate_image_url("https://cdn.example.com/test.png")


def test_validate_image_url_allows_literal_public_ip():
    from services.providers._net import validate_image_url
    # Literal public IP — no DNS lookup, tests IP-check path directly
    assert validate_image_url("https://8.8.8.8/image.png")
