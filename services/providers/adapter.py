"""
services/providers/adapter.py — Unified provider adapter interface
─────────────────────────────────────────────────────────────────
Defines the Protocol that all provider adapters should implement.
This is Phase 1 of NET-03: existing providers continue to work via
their try_* functions, but new adapters can implement this interface
for better testability and error mapping.
"""
from __future__ import annotations

from typing import Callable, Optional, Protocol, Tuple

from services.generation.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderPolicyError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderTransientError,
    classify_http_error,
)


class ImageProvider(Protocol):
    """Protocol for image generation providers."""

    @property
    def provider_id(self) -> str:
        """Stable provider identifier (e.g. 'siliconflow')."""
        ...

    @property
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        ...

    @property
    def supports_img2img(self) -> bool:
        """Whether this provider supports image-to-image generation."""
        ...

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int,
        cfg: dict,
        log: Callable[[str], None],
        reference_image: Optional[bytes] = None,
        strength: float = 0.6,
    ) -> Tuple[bytes, str]:
        """
        Generate an image.

        Returns: (image_bytes, provider_display_name)

        Raises:
            ProviderAuthError: Invalid/missing API key
            ProviderQuotaError: Out of quota/balance
            ProviderRateLimitError: Rate limited (429)
            ProviderTransientError: Temporary failure (5xx, timeout)
            ProviderPolicyError: Content rejected
            ProviderInvalidRequestError: Bad parameters
        """
        ...


def map_http_error(status_code: int, message: str = "") -> ProviderError:
    """Map HTTP status code to appropriate ProviderError."""
    return classify_http_error(status_code, message)
