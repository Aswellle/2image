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
