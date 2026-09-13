"""
services/generation/downloader.py — Bounded secure image download
─────────────────────────────────────────────────────────────────
Replaces the old ``safe_get_image()`` in ``_net.py`` with:
  - Max byte cap (streaming, not buffered)
  - Content-Type allowlist
  - Connect/read timeouts
  - SSRF redirect validation
  - Cancellation/deadline hooks
"""
from __future__ import annotations

import logging
from typing import Callable

import requests

from services.generation.cancellation import CancellationToken, Deadline
from services.generation.errors import (
    ProviderInvalidResponseError,
    ProviderPayloadTooLargeError,
    ProviderTransientError,
)
from services.providers._net import validate_image_url

log = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}
CHUNK_SIZE = 64 * 1024
MAX_REDIRECT_HOPS = 5
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 30.0


def bounded_download(
    url: str,
    session: requests.Session | None = None,
    token: CancellationToken | None = None,
    deadline: Deadline | None = None,
    max_bytes: int = MAX_IMAGE_BYTES,
    allowed_types: set[str] | None = None,
    log_cb: Callable[[str], None] | None = None,
) -> bytes:
    """
    Download an image URL with full safety bounds.

    Raises:
        ProviderInvalidResponseError  — bad content-type or URL
        ProviderPayloadTooLargeError  — exceeds max_bytes
        ProviderTransientError        — network/timeout
        GenerationCancelled           — user cancelled
        DeadlineExceeded              — deadline reached
    """
    if allowed_types is None:
        allowed_types = ALLOWED_IMAGE_TYPES

    if not validate_image_url(url):
        raise ProviderInvalidResponseError(f"Blocked unsafe image URL: {url[:100]}")

    sess = session or requests

    try:
        resp = _follow_redirects(sess, url, token, deadline)
        resp.raise_for_status()
    except requests.Timeout as exc:
        raise ProviderTransientError(f"Download timeout: {exc}") from exc
    except requests.ConnectionError as exc:
        raise ProviderTransientError(f"Connection failed: {exc}") from exc
    except (ProviderInvalidResponseError, ProviderPayloadTooLargeError):
        raise
    except Exception as exc:
        raise ProviderTransientError(f"Download failed: {exc}") from exc

    # Validate content-type
    content_type = resp.headers.get("Content-Type", "").split(";", 1)[0].lower().strip()
    if content_type and content_type not in allowed_types:
        raise ProviderInvalidResponseError(
            f"Unsupported content type: {content_type}"
        )

    # Check Content-Length header first
    length = resp.headers.get("Content-Length")
    if length and int(length) > max_bytes:
        raise ProviderPayloadTooLargeError(
            f"Content-Length {length} exceeds max {max_bytes}"
        )

    # Stream with size cap
    data = bytearray()
    try:
        for chunk in resp.iter_content(CHUNK_SIZE):
            if token:
                token.throw_if_cancelled()
            if deadline:
                deadline.assert_alive()
            if chunk:
                data.extend(chunk)
                if len(data) > max_bytes:
                    raise ProviderPayloadTooLargeError(
                        f"Download exceeded {max_bytes} bytes"
                    )
    except requests.Timeout as exc:
        raise ProviderTransientError(f"Read timeout: {exc}") from exc

    if not data:
        raise ProviderInvalidResponseError("Empty image response")

    if log_cb:
        log_cb(f"Downloaded {len(data) // 1024} KB from {url[:60]}…")

    return bytes(data)


def _follow_redirects(
    session: requests.Session,
    url: str,
    token: CancellationToken | None,
    deadline: Deadline | None,
):
    """Follow redirects with SSRF validation at each hop."""
    current_url = url
    for hop in range(MAX_REDIRECT_HOPS + 1):
        if token:
            token.throw_if_cancelled()
        if deadline:
            deadline.assert_alive()

        if not validate_image_url(current_url):
            raise ProviderInvalidResponseError(
                f"Redirect to unsafe URL blocked: {current_url[:100]}"
            )

        resp = session.get(
            current_url,
            stream=True,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            allow_redirects=False,
        )

        if not (300 <= resp.status_code < 400):
            return resp

        location = resp.headers.get("Location")
        if not location:
            raise ProviderInvalidResponseError("Redirect with no Location header")

        from urllib.parse import urlparse

        parsed = urlparse(location)
        if not parsed.scheme:
            # Relative redirect — resolve against current URL
            from urllib.parse import urljoin

            current_url = urljoin(current_url, location)
        else:
            current_url = location

    raise ProviderInvalidResponseError(
        f"Too many redirects (>{MAX_REDIRECT_HOPS})"
    )
