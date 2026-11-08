"""
services/generation/errors.py — Provider error taxonomy
──────────────────────────────────────────────────────
Every provider HTTP/status error MUST be mapped to one of these
domain exceptions. The orchestrator decides retry/fallback based
on ``retryable`` and ``fallback`` flags — NOT on HTTP codes.

Mapping guide:
  400/422           → ProviderInvalidRequestError
  401               → ProviderAuthError
  402 / balance     → ProviderQuotaError
  403               → ProviderAuthError (or ProviderPolicyError)
  404               → ProviderAuthError
  408               → ProviderTransientError
  429               → ProviderRateLimitError
  500/502/503/504   → ProviderTransientError
  ConnectionError   → ProviderTransientError
  Timeout           → ProviderTransientError
  JSON decode fail  → ProviderTransientError (retry once)
  Image validate    → ProviderInvalidResponseError
"""

from __future__ import annotations

# ── 按错误码的「下一步」用户指引（zh-CN）────────────────────────
# 与 ProviderError.code 一一对应；UI 弹窗 / 状态栏 / 日志记录共用，
# 让用户对每个失败类型都知道下一步该做什么。
NEXT_STEP_BY_CODE: dict[str, str] = {
    "not_configured": "在「🆓 免费配置」或「💎 付费接口配置」中填写该接口的 API Key",
    "auth_failed": "打开配置向导重新粘贴该接口的 API Key，确认账号有效且 Key 未被重置",
    "quota_exhausted": "前往该接口的控制台充值，或等待调度器自动尝试其他接口",
    "rate_limited": "等待约 30 秒再试；批量任务会自动退避重试",
    "policy_rejected": "调整提示词（移除敏感词/真人名/品牌）或更换其他接口",
    "invalid_request": "更换尺寸或模型组合后重试；该接口已被自动跳过",
    "invalid_response": "稍后重试；若持续出现多为该接口服务端异常，可切换其他接口",
    "transient": "检查网络/代理后重试；批量任务会自动退避并尝试其他接口",
    "provider_error": "查看「调试日志」中的完整错误详情",
}


class ProviderError(ValueError):
    """Base for all provider-domain errors.

    Inherits ValueError so the legacy provider contract
    ("raise ValueError → fall through to next provider") keeps working
    everywhere that catches ValueError while the orchestrator gets
    precise ``code``/``retryable`` semantics.
    """

    code: str = "provider_error"
    retryable: bool = False
    fallback: bool = True

    def __init__(self, message: str = "", provider: str | None = None) -> None:
        super().__init__(message)
        # 产生错误的接口（稳定 ID）；_net 的统一抛错出口会填充，
        # provider 内的本地 raise 不传则保持 None（消息自带接口名）。
        self.provider = provider

    @property
    def next_step(self) -> str:
        """按错误码的用户下一步指引（zh-CN），UI / 日志共用。"""
        return NEXT_STEP_BY_CODE.get(self.code, "")


class ProviderConfigError(ProviderError):
    """Provider selected but credentials missing/invalid format.

    Distinct from auth failure: nothing was sent to the API, so the
    message carries user-facing setup guidance. Never retried.
    """

    code = "not_configured"
    retryable = False
    fallback = True


class ProviderAuthError(ProviderError):
    """401 / 403 / invalid key — never retry this provider.

    fallback=True (not False): a bad key on one provider mid-chain must
    fall through to the next candidate, not abort the whole job. The
    "stop everything" semantic is reserved for caller errors
    (ProviderInvalidRequestError), where every provider would fail
    identically.
    """

    code = "auth_failed"
    retryable = False
    fallback = True


class ProviderQuotaError(ProviderError):
    """402 / balance exhausted / billing required."""

    code = "quota_exhausted"
    retryable = False
    fallback = True


class ProviderRateLimitError(ProviderError):
    """429 — retry after backoff."""

    code = "rate_limited"
    retryable = True
    fallback = True

    def __init__(self, msg: str = "rate limited", retry_after: float | None = None):
        super().__init__(msg)
        self.retry_after = retry_after


class ProviderTransientError(ProviderError):
    """5xx / connection / timeout — retry with backoff then fallback."""

    code = "transient"
    retryable = True
    fallback = True


class ProviderPolicyError(ProviderError):
    """Content policy rejection — don't retry, may try next provider."""

    code = "policy_rejected"
    retryable = False
    fallback = True


class ProviderInvalidRequestError(ProviderError):
    """400/422 — caller error, never retry."""

    code = "invalid_request"
    retryable = False
    fallback = False


class ProviderInvalidResponseError(ProviderError):
    """Response parsed but image/content invalid — don't repeat same request."""

    code = "invalid_response"
    retryable = False
    fallback = True


class ProviderPayloadTooLargeError(ProviderError):
    """Download exceeded size cap."""

    code = "payload_too_large"
    retryable = False
    fallback = True


class GenerationCancelled(Exception):
    """User-requested cancellation — not a provider error."""

    code = "cancelled"


class DeadlineExceeded(Exception):
    """Absolute job deadline reached."""

    code = "deadline_exceeded"


def classify_http_error(status_code: int, message: str = "", provider: str | None = None) -> ProviderError:
    """
    Convert an HTTP status code to the appropriate ProviderError.

    This is the SINGLE source of truth for HTTP→domain mapping.
    All provider adapters MUST use this instead of hand-mapping.

    ``provider``（可选）写入错误的 .provider 属性，供 UI 弹窗与
    结构化日志标注失败来源。
    """
    err: ProviderError
    if status_code in (400, 422):
        err = ProviderInvalidRequestError(message or f"HTTP {status_code}")
    elif status_code == 401:
        err = ProviderAuthError(message or "Unauthorized")
    elif status_code == 402:
        err = ProviderQuotaError(message or "Payment required")
    elif status_code == 403:
        err = ProviderAuthError(message or "Forbidden")
    elif status_code == 404:
        err = ProviderAuthError(message or "Not found")
    elif status_code == 408:
        err = ProviderTransientError(message or "Request timeout")
    elif status_code == 429:
        err = ProviderRateLimitError(message or "Rate limited")
    elif status_code in (500, 502, 503, 504):
        err = ProviderTransientError(message or f"HTTP {status_code}")
    elif status_code >= 500:
        err = ProviderTransientError(message or f"HTTP {status_code}")
    elif status_code >= 400:
        err = ProviderInvalidRequestError(message or f"HTTP {status_code}")
    else:
        err = ProviderError(message or f"Unexpected HTTP {status_code}")
    if provider:
        err.provider = provider
    return err


def format_error_record(err: BaseException) -> str:
    """把异常格式化为单行结构化记录（写 debug.log 用）。

    ProviderError → ``code=… provider=… detail=… next=…``；
    其他异常 → ``code=unhandled type=… detail=…``。
    """
    if isinstance(err, ProviderError):
        detail = str(err).replace("\n", " ")
        provider = getattr(err, "provider", None) or "-"
        next_step = err.next_step or "-"
        return f"code={err.code} provider={provider} detail={detail[:300]} next={next_step}"
    detail = f"{type(err).__name__}: {err}".replace("\n", " ")
    return f"code=unhandled provider=- detail={detail[:300]} next=查看「调试日志」"
