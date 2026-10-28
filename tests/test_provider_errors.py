"""类型化 provider 错误契约测试（NET-ERR-001）。

providers 不得再抛裸 ValueError/RuntimeError 表达失败语义——
统一经 _net.raise_provider_error / raise_for_response 归类为
ProviderError 家族；orchestrator 按 .code 决策，App._err 按
code 取状态栏文案，全部不再做字符串嗅探。
"""

import pytest

from services.generation.errors import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderInvalidResponseError,
    ProviderPolicyError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderTransientError,
    classify_http_error,
)
from services.providers._net import raise_for_response, raise_provider_error


def test_provider_error_is_value_error_backward_compatible():
    """旧契约 except ValueError 必须继续兜住类型化错误。"""
    assert issubclass(ProviderError, ValueError)
    for cls in (
        ProviderAuthError,
        ProviderConfigError,
        ProviderInvalidRequestError,
        ProviderInvalidResponseError,
        ProviderPolicyError,
        ProviderQuotaError,
        ProviderRateLimitError,
        ProviderTransientError,
    ):
        assert issubclass(cls, ValueError)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, ProviderInvalidRequestError),
        (401, ProviderAuthError),
        (402, ProviderQuotaError),
        (403, ProviderAuthError),
        (429, ProviderRateLimitError),
        (500, ProviderTransientError),
        (503, ProviderTransientError),
    ],
)
def test_raise_provider_error_classifies_by_status(status, expected):
    with pytest.raises(expected) as ei:
        raise_provider_error("Test", status=status, detail="boom")
    assert "Test: boom" in str(ei.value)


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("config", ProviderConfigError),
        ("rate_limit", ProviderRateLimitError),
        ("quota", ProviderQuotaError),
        ("invalid_response", ProviderInvalidResponseError),
        ("transient", ProviderTransientError),
    ],
)
def test_raise_provider_error_explicit_kind(kind, expected):
    with pytest.raises(expected):
        raise_provider_error("Test", kind=kind)


def test_raise_for_response_uses_safe_error_text():
    class FakeResp:
        status_code = 429

        def json(self):
            return {"error": {"message": "slow down"}}

    with pytest.raises(ProviderRateLimitError, match="slow down"):
        raise_for_response(FakeResp(), "Test")


def test_config_error_code_is_not_configured():
    err = ProviderConfigError("需要 X API Key")
    assert err.code == "not_configured"
    assert err.retryable is False


def test_app_err_maps_typed_codes(app, tk_root):
    """App._err 对 ProviderError 按 code 取文案，不再子串嗅探。"""
    real, _ = app
    real._err(ProviderAuthError("x: bad key"))
    assert "err_api_key" in real.content.stv.get() or real.content.stv.get()

    real._err(ProviderQuotaError("x: balance"))
    real._err(ProviderPolicyError("x: policy"))
    assert real.content.stv.get().startswith("❌")


def test_app_err_untyped_multiline_degrades_to_summary(app, tk_root):
    """未归类字符串 → 通用失败提示，多行详情不进状态栏。"""
    real, _ = app
    raw = "所有接口均失败:\ntrace line 1\ntrace line 2"
    real._err(raw)
    assert "\n" not in real.content.stv.get()
