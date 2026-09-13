"""
services/generation/__init__.py — Generation core package
─────────────────────────────────────────────────────────
Holds error taxonomy, retry policy, health tracking,
orchestrator, and router.  The old ``image_service.py``
becomes a thin façade that delegates here.
"""
from services.generation.cancellation import CancellationToken, Deadline
from services.generation.errors import (
    DeadlineExceeded,
    GenerationCancelled,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderInvalidResponseError,
    ProviderPayloadTooLargeError,
    ProviderPolicyError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderTransientError,
    classify_http_error,
)
from services.generation.retry_policy import RetryPolicy, get_retry_policy

__all__ = [
    "CancellationToken",
    "Deadline",
    "DeadlineExceeded",
    "GenerationCancelled",
    "ProviderAuthError",
    "ProviderError",
    "ProviderInvalidRequestError",
    "ProviderInvalidResponseError",
    "ProviderPayloadTooLargeError",
    "ProviderPolicyError",
    "ProviderQuotaError",
    "ProviderRateLimitError",
    "ProviderTransientError",
    "RetryPolicy",
    "classify_http_error",
    "get_retry_policy",
]
