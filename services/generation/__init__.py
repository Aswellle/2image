"""
services/generation/__init__.py — Generation core package
─────────────────────────────────────────────────────────
Job orchestration, routing, health tracking, and metrics.
Holds error taxonomy, retry policy, health tracking,
orchestrator, router, and job queue.
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
