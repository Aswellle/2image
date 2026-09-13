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


class ProviderError(Exception):
    """Base for all provider-domain errors."""

    code: str = "provider_error"
    retryable: bool = False
    fallback: bool = True


class ProviderAuthError(ProviderError):
    """401 / 403 / invalid key — never retry this provider."""

    code = "auth_failed"
    retryable = False
    fallback = False


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


def classify_http_error(status_code: int, message: str = "") -> ProviderError:
    """
    Convert an HTTP status code to the appropriate ProviderError.

    This is the SINGLE source of truth for HTTP→domain mapping.
    All provider adapters MUST use this instead of hand-mapping.
    """
    if status_code in (400, 422):
        return ProviderInvalidRequestError(message or f"HTTP {status_code}")
    if status_code == 401:
        return ProviderAuthError(message or "Unauthorized")
    if status_code == 402:
        return ProviderQuotaError(message or "Payment required")
    if status_code == 403:
        return ProviderAuthError(message or "Forbidden")
    if status_code == 404:
        return ProviderAuthError(message or "Not found")
    if status_code == 408:
        return ProviderTransientError(message or "Request timeout")
    if status_code == 429:
        return ProviderRateLimitError(message or "Rate limited")
    if status_code in (500, 502, 503, 504):
        return ProviderTransientError(message or f"HTTP {status_code}")
    if status_code >= 500:
        return ProviderTransientError(message or f"HTTP {status_code}")
    if status_code >= 400:
        return ProviderInvalidRequestError(message or f"HTTP {status_code}")
    return ProviderError(message or f"Unexpected HTTP {status_code}")
