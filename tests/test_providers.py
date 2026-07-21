"""Tests for provider error handling."""
import pytest


def test_gemini_missing_key_raises_valueerror():
    from services.providers.gemini import try_gemini
    with pytest.raises(ValueError, match="API Key"):
        try_gemini("test prompt", 512, 512, 42, {"gemini_key": ""}, print)


def test_openai_image_missing_key_raises_valueerror():
    from services.providers.openai_image import try_openai_image
    with pytest.raises(ValueError, match="API Key"):
        try_openai_image("test prompt", 1024, 1024, 42, {"openai_key": ""}, print)


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
    ("services.providers.gemini_nano_banana_pro", "try_gemini_nano_banana_pro", {"gemini_key": ""}),
    ("services.providers.minimax_image", "try_minimax_image", {"minimax_key": ""}),
    ("services.providers.dashscope_qwen","try_dashscope_qwen",{"dashscope_key": ""}),
    ("services.providers.bfl_flux",      "try_bfl_flux",      {"bfl_key": ""}),
    ("services.providers.bria_ai",       "try_bria_ai",       {"bria_key": ""}),
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


def test_validate_image_url_blocks_ipv4_mapped_ipv6_loopback():
    from services.providers._net import validate_image_url
    from unittest.mock import patch
    import socket
    # ::ffff:127.0.0.1 — IPv4-mapped loopback; must be unwrapped and blocked
    mock_result = [(socket.AF_INET6, socket.SOCK_STREAM, 6, '',
                    ('::ffff:127.0.0.1', 443, 0, 0))]
    with patch('services.providers._net.socket.getaddrinfo', return_value=mock_result):
        assert not validate_image_url("https://cdn.example.com/img.png")


def test_validate_image_url_blocks_ipv4_mapped_ipv6_link_local():
    from services.providers._net import validate_image_url
    from unittest.mock import patch
    import socket
    # ::ffff:169.254.169.254 — cloud metadata via IPv6 literal
    mock_result = [(socket.AF_INET6, socket.SOCK_STREAM, 6, '',
                    ('::ffff:169.254.169.254', 443, 0, 0))]
    with patch('services.providers._net.socket.getaddrinfo', return_value=mock_result):
        assert not validate_image_url("https://metadata.internal/latest/")


def test_validate_image_url_blocks_native_ipv6_loopback():
    from services.providers._net import validate_image_url
    assert not validate_image_url("https://[::1]/img.png")


def test_validate_image_url_allows_literal_public_ip():
    from services.providers._net import validate_image_url
    # Literal public IP — no DNS lookup, tests IP-check path directly
    assert validate_image_url("https://8.8.8.8/image.png")


# ── Network-failure regression tests (P3-B) ──────────────────────────────────
# Before the fix: 13 providers caught requests.exceptions.ConnectionError without
# importing requests → NameError at exception-handling time, escaping the
# dispatcher's catch and killing the whole generation thread.
# After fix: import requests is present, so ValueError is raised instead.

import requests as _requests

_NETWORK_FAILURE_CASES = [
    ("services.providers.siliconflow",   "try_siliconflow",   {"sf_key": "x"},                                  "post"),
    ("services.providers.huggingface",   "try_hf_inference",  {"hf_token": "x"},                               "post"),
    ("services.providers.pollinations",  "try_pollinations",  {},                                               "get"),
    ("services.providers.cloudflare_ai","try_cloudflare_ai",  {"cf_account_id": "x", "cf_api_token": "x"},     "post"),
    ("services.providers.segmind",       "try_segmind",       {"segmind_key": "x"},                            "post"),
    ("services.providers.stablehorde",   "try_stablehorde",   {},                                               "post"),
    ("services.providers.recraft",       "try_recraft",       {"recraft_key": "x"},                            "post"),
    ("services.providers.modelslab",     "try_modelslab",     {"modelslab_key": "x"},                          "post"),
    ("services.providers.ideogram",      "try_ideogram",      {"ideogram_key": "x"},                           "post"),
    ("services.providers.gemini",        "try_gemini",        {"gemini_key": "x"},                             "post"),
    ("services.providers.openrouter",    "try_openrouter",    {"openrouter_key": "x"},                         "post"),
    ("services.providers.together_ai",   "try_together_ai",   {"together_key": "x"},                           "post"),
    ("services.providers.xai_grok",      "try_xai_grok",      {"xai_key": "x"},                               "post"),
]


@pytest.mark.parametrize("module,fn,cfg,method", _NETWORK_FAILURE_CASES,
                          ids=[c[1] for c in _NETWORK_FAILURE_CASES])
def test_provider_connection_error_not_nameerror(module, fn, cfg, method):
    """A network failure must surface as ValueError/RuntimeError/TimeoutError,
    never NameError (which would indicate missing `import requests`)."""
    from unittest.mock import patch
    from services.providers import _net
    mod = importlib.import_module(module)
    func = getattr(mod, fn)
    conn_err = _requests.exceptions.ConnectionError("simulated network down")
    with patch.object(_net.SESSION, method, side_effect=conn_err):
        with pytest.raises((ValueError, RuntimeError, TimeoutError)):
            func("test prompt", 512, 512, 42, cfg, print)


# ── safe_get_image redirect-chain tests (TC-H3) ───────────────────────────────

def _make_redirect(location: str):
    """Helper: mock response that redirects to `location`."""
    from unittest.mock import MagicMock
    r = MagicMock()
    r.status_code = 302
    r.headers = {"Location": location}
    return r


def _make_ok(content: bytes = b"image-bytes"):
    from unittest.mock import MagicMock
    r = MagicMock()
    r.status_code = 200
    r.content = content
    r.raise_for_status = lambda: None
    return r


def test_safe_get_image_happy_path():
    from unittest.mock import patch
    from services.providers._net import safe_get_image, SESSION
    with patch.object(SESSION, "get", return_value=_make_ok(b"img")):
        result = safe_get_image("https://8.8.8.8/img.png")
    assert result == b"img"


def test_safe_get_image_single_valid_redirect_followed():
    from unittest.mock import patch, call
    from services.providers._net import safe_get_image, SESSION, validate_image_url
    responses = [_make_redirect("https://8.8.8.8/final.png"), _make_ok(b"redirected")]
    with patch.object(SESSION, "get", side_effect=responses):
        result = safe_get_image("https://8.8.8.8/first.png")
    assert result == b"redirected"


def test_safe_get_image_redirect_to_private_ip_blocked():
    """Redirect chain that leads to a private IP must raise ValueError mid-chain."""
    from unittest.mock import patch
    from services.providers._net import safe_get_image, SESSION
    # First response redirects to a private IP
    responses = [_make_redirect("https://192.168.1.1/steal.png")]
    with patch.object(SESSION, "get", side_effect=responses):
        with pytest.raises(ValueError, match="[Bb]locked"):
            safe_get_image("https://8.8.8.8/start.png")


def test_safe_get_image_redirect_to_http_blocked():
    """Redirect to HTTP (non-HTTPS) must be blocked by validate_image_url."""
    from unittest.mock import patch
    from services.providers._net import safe_get_image, SESSION
    responses = [_make_redirect("http://cdn.example.com/img.png")]
    with patch.object(SESSION, "get", side_effect=responses):
        with pytest.raises(ValueError, match="[Bb]locked"):
            safe_get_image("https://8.8.8.8/start.png")


def test_safe_get_image_five_valid_hops_succeed():
    """Exactly 5 redirects (max_hops) before a 200 should succeed."""
    from unittest.mock import patch
    from services.providers._net import safe_get_image, SESSION
    # 5 redirects then a 200
    responses = [_make_redirect("https://8.8.8.8/hop.png")] * 5 + [_make_ok(b"final")]
    with patch.object(SESSION, "get", side_effect=responses):
        result = safe_get_image("https://8.8.8.8/start.png")
    assert result == b"final"


def test_safe_get_image_six_hops_stops_after_five():
    """After 5 redirect hops the loop exits; the 6th redirect response is treated
    as the final response and raise_for_status is called on it."""
    from unittest.mock import patch, MagicMock
    from services.providers._net import safe_get_image, SESSION
    sixth_redirect = MagicMock()
    sixth_redirect.status_code = 302
    sixth_redirect.headers = {"Location": "https://8.8.8.8/seventh.png"}
    sixth_redirect.raise_for_status = lambda: None
    sixth_redirect.content = b""
    responses = [_make_redirect("https://8.8.8.8/hop.png")] * 5 + [sixth_redirect]
    with patch.object(SESSION, "get", side_effect=responses):
        # Loop runs max_hops=5 times; 6th redirect is left as-is (still a 3xx)
        # raise_for_status on a 302 mock does nothing here, so content is returned
        safe_get_image("https://8.8.8.8/start.png")  # should not raise


def test_safe_get_image_initial_invalid_url_raises_valueerror():
    from services.providers._net import safe_get_image
    with pytest.raises(ValueError, match="[Bb]locked"):
        safe_get_image("http://example.com/img.png")
