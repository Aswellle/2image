"""
services/updater/manifest.py — update.json manifest protocol
────────────────────────────────────────────────────────────
The static asset ``releases/latest/download/update.json`` is the ONLY
production update channel: no Releases API, no rate limit, no HTML
scraping.  Every field is validated before anything is trusted — a
manifest that fails any rule must never lead to a download, let alone
an install.  Download URLs are restricted to the project's GitHub
Release hosts (allowlist, HTTPS only).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from services.generation.cancellation import CancellationToken
from services.updater.errors import UpdateError, UpdateErrorCode
from services.updater.version import parse_version

REPO_OWNER = "Aswellle"
REPO_NAME = "2image"
MANIFEST_URL = (f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
                "/releases/latest/download/update.json")
RELEASES_PAGE = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/latest"

MANIFEST_ASSET_KEY = "windows-x64-installer"
SUPPORTED_SCHEMA_VERSION = 1
STABLE_CHANNEL = "stable"

# Redirect targets of GitHub release assets must stay inside this set.
ALLOWED_DOWNLOAD_HOSTS = frozenset({
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
})

_CONNECT_TIMEOUT = 10.0
_READ_TIMEOUT = 30.0


@dataclass(frozen=True)
class UpdateAsset:
    file_name: str
    download_url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class UpdateManifest:
    schema_version: int
    channel: str
    version: str
    tag: str
    published_at: str
    release_url: str
    notes_url: str
    mandatory: bool
    minimum_supported_version: str
    installer: UpdateAsset


def _invalid(detail: str) -> UpdateError:
    return UpdateError(UpdateErrorCode.MANIFEST_INVALID, detail)


def _url_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host not in ALLOWED_DOWNLOAD_HOSTS:
        return False
    if host == "github.com":
        prefix = f"/{REPO_OWNER}/{REPO_NAME}/releases/"
        return parsed.path.startswith(prefix)
    return True


def validate_manifest(payload: object) -> UpdateManifest:
    """Structurally validate a decoded manifest and build the model.

    Raises UpdateError(MANIFEST_INVALID / VERSION_INVALID) on ANY rule
    violation — callers must treat that as "refuse to update", never as
    "no update available".
    """
    if not isinstance(payload, dict):
        raise _invalid("manifest is not a JSON object")
    if payload.get("schemaVersion") != SUPPORTED_SCHEMA_VERSION:
        raise _invalid(f"unsupported schemaVersion: {payload.get('schemaVersion')!r}")
    if payload.get("channel") != STABLE_CHANNEL:
        raise _invalid(f"unsupported channel: {payload.get('channel')!r}")

    version = str(payload.get("version") or "").strip()
    if not version:
        raise _invalid("version is empty")
    try:
        parse_version(version)
    except ValueError as exc:
        raise UpdateError(UpdateErrorCode.VERSION_INVALID, str(exc)) from exc

    tag = str(payload.get("tag") or "").strip() or f"v{version}"
    assets = payload.get("assets")
    if not isinstance(assets, dict) or MANIFEST_ASSET_KEY not in assets:
        raise _invalid(f"missing asset: {MANIFEST_ASSET_KEY}")
    raw = assets[MANIFEST_ASSET_KEY]
    if not isinstance(raw, dict):
        raise _invalid("asset entry is not an object")

    file_name = str(raw.get("fileName") or "").strip()
    url = str(raw.get("downloadUrl") or "").strip()
    sha256 = str(raw.get("sha256") or "").strip().lower()
    size = raw.get("size")
    if not file_name:
        raise _invalid("asset fileName is empty")
    if not _url_allowed(url):
        raise _invalid(f"downloadUrl not allowed: {url!r}")
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise _invalid("asset sha256 is not a 64-hex digest")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise _invalid(f"asset size invalid: {size!r}")

    return UpdateManifest(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        channel=STABLE_CHANNEL,
        version=version,
        tag=tag,
        published_at=str(payload.get("publishedAt") or ""),
        release_url=str(payload.get("releaseUrl") or RELEASES_PAGE),
        notes_url=str(payload.get("releaseNotesUrl") or RELEASES_PAGE),
        mandatory=bool(payload.get("mandatory", False)),
        minimum_supported_version=str(payload.get("minimumSupportedVersion") or ""),
        installer=UpdateAsset(file_name, url, size, sha256),
    )


def evaluate_manifest(payload: object, current_version: str) -> UpdateManifest | None:
    """Validate + compare against the running version.

    Returns the manifest when a strictly newer stable version exists,
    None when the manifest is valid but not newer (no update), and
    raises for any structural violation.
    """
    manifest = validate_manifest(payload)
    if not (parse_version(manifest.version) > parse_version(current_version)):
        return None
    return manifest


def fetch_manifest(
    current_version: str,
    session: requests.Session | None = None,
    timeout: tuple[float, float] = (_CONNECT_TIMEOUT, _READ_TIMEOUT),
    retries: int = 2,
    backoff: float = 1.5,
    token: CancellationToken | None = None,
) -> UpdateManifest | None:
    """Fetch + validate the stable-channel manifest.

    Returns None when the server manifest is not newer than the running
    build.  Network/HTTP failures retry ``retries`` times with a short
    backoff, then raise UpdateError(NETWORK_ERROR / HTTP_ERROR);
    HTTP 404 (manifest not published yet) is permanent — it must be
    reported as a failed check, never as "up to date".
    """
    if session is None:
        from services.providers._net import get_session
        session = get_session()

    attempts = max(1, retries + 1)
    last_error: UpdateError | None = None
    for attempt in range(attempts):
        if token is not None:
            token.throw_if_cancelled()
        try:
            resp = session.get(MANIFEST_URL, timeout=timeout)
            if resp.status_code == 404:
                raise UpdateError(
                    UpdateErrorCode.HTTP_ERROR,
                    "update.json not found (HTTP 404)")
            if 500 <= resp.status_code < 600:
                raise UpdateError(
                    UpdateErrorCode.HTTP_ERROR,
                    f"manifest server error (HTTP {resp.status_code})")
            if resp.status_code != 200:
                raise UpdateError(
                    UpdateErrorCode.HTTP_ERROR,
                    f"unexpected HTTP {resp.status_code}")
            try:
                payload = resp.json()
            except ValueError as exc:
                raise _invalid(f"malformed manifest JSON: {exc}") from exc
            return evaluate_manifest(payload, current_version)
        except UpdateError as exc:
            permanent = (exc.code in (UpdateErrorCode.MANIFEST_INVALID,
                                      UpdateErrorCode.VERSION_INVALID)
                         or "404" in exc.detail)
            if permanent or attempt >= attempts - 1:
                raise
            last_error = exc
        except requests.RequestException as exc:
            if attempt >= attempts - 1:
                raise UpdateError(
                    UpdateErrorCode.NETWORK_ERROR,
                    f"manifest request failed: {type(exc).__name__}") from exc
            last_error = UpdateError(
                UpdateErrorCode.NETWORK_ERROR,
                f"manifest request failed: {type(exc).__name__}")
        # Retryable failure: interruptible short backoff, then retry.
        if token is not None and token.wait(backoff):
            token.throw_if_cancelled()
        else:
            time.sleep(backoff)
    raise last_error or UpdateError(UpdateErrorCode.NETWORK_ERROR, "unreachable")
