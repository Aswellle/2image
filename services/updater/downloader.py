"""
services/updater/downloader.py — streaming download + integrity gate
────────────────────────────────────────────────────────────────────
Download lifecycle (see the update plan, §8):

    <update_root>/<version>/<file>.exe.partial   (streaming)
        → size == manifest.size                  (mandatory)
        → SHA-256 == manifest.sha256             (mandatory, hash deleted)
        → atomic rename to the final name        (only verified files)

The download URL host is re-checked against the manifest allowlist
(defense in depth) and the post-redirect response host is re-checked as
well.  Transient failures retry with a short backoff; cancellation
always removes the partial file.
"""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Callable

import requests

from services.generation.cancellation import CancellationToken
from services.generation.errors import GenerationCancelled

from services.updater.errors import (
    ChecksumMismatchError,
    UpdateError,
    UpdateErrorCode,
)
from services.updater.manifest import UpdateAsset, _url_allowed

CHUNK_SIZE = 128 * 1024
MAX_ASSET_BYTES = 200 * 1024 * 1024   # installer ~20-40 MB; generous cap
CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 30.0

# progress(stage, done_bytes, total_bytes, speed_bps); stage ∈ {"download", "verify"}
ProgressCb = Callable[[str, int, int, float], None]


def sha256_file(path: Path, progress: ProgressCb | None = None,
                token: CancellationToken | None = None) -> str:
    """Chunked SHA-256 of a local file (cancellation-aware)."""
    digest = hashlib.sha256()
    size = path.stat().st_size
    done = 0
    with open(path, "rb") as fh:
        while True:
            if token is not None:
                token.throw_if_cancelled()
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            done += len(chunk)
            if progress is not None:
                progress("verify", done, size, 0.0)
    return digest.hexdigest()


def _silent_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _already_verified(final: Path, asset: UpdateAsset) -> bool:
    """A previous run may have left a fully verified package — reuse it."""
    try:
        if final.stat().st_size != asset.size:
            return False
        return sha256_file(final) == asset.sha256
    except (OSError, GenerationCancelled):
        return False


def download_verified(
    asset: UpdateAsset,
    dest_dir: Path,
    token: CancellationToken | None = None,
    progress: ProgressCb | None = None,
    session: requests.Session | None = None,
    retries: int = 2,
    backoff: float = 2.0,
    max_bytes: int = MAX_ASSET_BYTES,
) -> Path:
    """Stream the manifest asset into ``dest_dir`` and verify it.

    Returns the path of the verified package.  Raises UpdateError with
    SIZE_MISMATCH / HASH_MISMATCH / DOWNLOAD_FAILED on any integrity or
    network failure; GenerationCancelled propagates after cleanup.
    """
    if not _url_allowed(asset.download_url):
        raise UpdateError(
            UpdateErrorCode.MANIFEST_INVALID,
            f"downloadUrl not allowed: {asset.download_url!r}")
    if session is None:
        from services.providers._net import get_session
        session = get_session()

    dest_dir.mkdir(parents=True, exist_ok=True)
    final = dest_dir / asset.file_name
    partial = Path(str(final) + ".partial")

    if _already_verified(final, asset):
        if progress is not None:
            progress("verify", asset.size, asset.size, 0.0)
        return final

    attempts = max(1, retries + 1)
    last_error: Exception | None = None
    for attempt in range(attempts):
        if token is not None:
            token.throw_if_cancelled()
        try:
            _download_once(asset, partial, token, progress, session,
                           max_bytes)
            break
        except (UpdateError, requests.RequestException, OSError,
                GenerationCancelled) as exc:
            _silent_unlink(partial)
            if isinstance(exc, GenerationCancelled):
                raise
            retryable = not isinstance(exc, UpdateError) or exc.code in (
                UpdateErrorCode.DOWNLOAD_FAILED,)
            if attempt >= attempts - 1 or not retryable:
                if isinstance(exc, UpdateError):
                    raise
                raise UpdateError(
                    UpdateErrorCode.DOWNLOAD_FAILED,
                    f"download failed: {type(exc).__name__}") from exc
            last_error = exc
            if token is not None and token.wait(backoff):
                token.throw_if_cancelled()
            else:
                time.sleep(backoff)
    else:  # pragma: no cover - loop always breaks or raises
        raise last_error or UpdateError(UpdateErrorCode.DOWNLOAD_FAILED)

    # Integrity gate — nothing unverified ever bears the final name.
    actual_size = partial.stat().st_size
    if actual_size != asset.size:
        _silent_unlink(partial)
        raise UpdateError(
            UpdateErrorCode.SIZE_MISMATCH,
            f"size mismatch: got {actual_size}, manifest says {asset.size}")
    actual_hash = sha256_file(partial, progress, token)
    if actual_hash != asset.sha256:
        _silent_unlink(partial)
        raise ChecksumMismatchError(
            f"sha256 mismatch: expected {asset.sha256[:16]}…, "
            f"got {actual_hash[:16]}… (download deleted)")
    os.replace(partial, final)
    return final


def _download_once(
    asset: UpdateAsset,
    partial: Path,
    token: CancellationToken | None,
    progress: ProgressCb | None,
    session: requests.Session,
    max_bytes: int,
) -> None:
    resp = session.get(asset.download_url, stream=True,
                       timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
    try:
        resp.raise_for_status()
        # Redirect target must stay inside the release asset hosts.
        if not _url_allowed(str(resp.url or asset.download_url)):
            raise UpdateError(
                UpdateErrorCode.MANIFEST_INVALID,
                f"redirect target not allowed: {resp.url!r}")
        total = asset.size
        done = 0
        started = time.monotonic()
        speed = 0.0
        with open(partial, "wb") as fh:
            for chunk in resp.iter_content(CHUNK_SIZE):
                if token is not None:
                    token.throw_if_cancelled()
                if not chunk:
                    continue
                fh.write(chunk)
                done += len(chunk)
                if done > max_bytes or (total and done > total):
                    raise UpdateError(
                        UpdateErrorCode.SIZE_MISMATCH,
                        f"download exceeds limit ({done} > "
                        f"{total or max_bytes} bytes)")
                if progress is not None:
                    elapsed = time.monotonic() - started
                    if elapsed > 0.2:
                        speed = done / elapsed
                    progress("download", done, total, speed)
        if total and done < total:
            raise UpdateError(
                UpdateErrorCode.DOWNLOAD_FAILED,
                f"incomplete download ({done}/{total} bytes)")
    finally:
        try:
            resp.close()
        except Exception:
            pass
