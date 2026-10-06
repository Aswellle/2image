"""update.json manifest validation matrix (§4.2): every rule violation
must be refused, and 404 must read as a failed check — never as
"up to date"."""
from unittest.mock import MagicMock

import pytest
import requests

from services.updater import manifest as mf
from services.updater.errors import UpdateError, UpdateErrorCode

VALID_SHA = "a" * 64


def _payload(**over):
    base = {
        "schemaVersion": 1,
        "channel": "stable",
        "version": "2.6.1",
        "tag": "v2.6.1",
        "publishedAt": "2026-10-06T00:00:00Z",
        "releaseUrl": "https://github.com/Aswellle/2image/releases/tag/v2.6.1",
        "releaseNotesUrl": "https://github.com/Aswellle/2image/releases/tag/v2.6.1",
        "mandatory": False,
        "minimumSupportedVersion": "0.0.0",
        "assets": {
            "windows-x64-installer": {
                "fileName": "2image-setup-v2.7.0.exe",
                "downloadUrl": ("https://github.com/Aswellle/2image/releases"
                                "/download/v2.7.0/2image-setup-v2.7.0.exe"),
                "size": 20480,
                "sha256": VALID_SHA,
            },
        },
    }
    for key, value in over.items():
        if key == "_asset":
            base["assets"]["windows-x64-installer"].update(value)
        else:
            base[key] = value
    return base


# ── structural validation ────────────────────────────────────

def test_valid_manifest_parses():
    m = mf.validate_manifest(_payload())
    assert m.version == "2.6.1"
    assert m.tag == "v2.6.1"
    assert m.installer.file_name == "2image-setup-v2.7.0.exe"
    assert m.installer.sha256 == VALID_SHA
    assert m.installer.size == 20480
    assert m.channel == "stable"


def test_rejects_non_object():
    with pytest.raises(UpdateError):
        mf.validate_manifest(["not", "a", "dict"])


def test_rejects_unknown_schema_version():
    with pytest.raises(UpdateError):
        mf.validate_manifest(_payload(schemaVersion=2))


def test_rejects_non_stable_channel():
    with pytest.raises(UpdateError):
        mf.validate_manifest(_payload(channel="beta"))


def test_rejects_empty_version():
    with pytest.raises(UpdateError):
        mf.validate_manifest(_payload(version=" "))


def test_rejects_non_semver_version():
    with pytest.raises(UpdateError) as ei:
        mf.validate_manifest(_payload(version="2.6"))
    assert ei.value.code is UpdateErrorCode.VERSION_INVALID


def test_rejects_missing_assets_block():
    p = _payload()
    del p["assets"]
    with pytest.raises(UpdateError):
        mf.validate_manifest(p)


def test_rejects_missing_windows_asset():
    p = _payload()
    del p["assets"]["windows-x64-installer"]
    with pytest.raises(UpdateError):
        mf.validate_manifest(p)


def test_rejects_empty_file_name():
    with pytest.raises(UpdateError):
        mf.validate_manifest(_payload(_asset={"fileName": ""}))


@pytest.mark.parametrize("url", [
    "http://github.com/Aswellle/2image/releases/download/v2.7.0/x.exe",
    "https://evil.example/x.exe",
    "https://github.com/other/repo/releases/download/v2.7.0/x.exe",
    "ftp://github.com/x.exe",
    "",
])
def test_rejects_disallowed_download_url(url):
    with pytest.raises(UpdateError):
        mf.validate_manifest(_payload(_asset={"downloadUrl": url}))


def test_allows_github_redirect_hosts():
    p = _payload(_asset={
        "downloadUrl": ("https://objects.githubusercontent.com/"
                        "some/release/asset")})
    assert mf.validate_manifest(p).installer.download_url.startswith(
        "https://objects.githubusercontent.com/")


@pytest.mark.parametrize("sha", ["", "abc123", "z" * 64, "A" * 63 + "g"])
def test_rejects_bad_sha256(sha):
    with pytest.raises(UpdateError):
        mf.validate_manifest(_payload(_asset={"sha256": sha}))


@pytest.mark.parametrize("size", [0, -1, "20480", 20.5, True, None])
def test_rejects_bad_size(size):
    with pytest.raises(UpdateError):
        mf.validate_manifest(_payload(_asset={"size": size}))


# ── evaluate vs current version ─────────────────────────────

def test_evaluate_returns_manifest_for_newer():
    m = mf.evaluate_manifest(_payload(), "2.6.0")
    assert m is not None and m.version == "2.6.1"


def test_evaluate_returns_none_for_same_or_older():
    assert mf.evaluate_manifest(_payload(), "2.6.1") is None
    assert mf.evaluate_manifest(_payload(), "2.7.0") is None


# ── fetch ────────────────────────────────────────────────────

def _session(resp=None, exc=None):
    session = MagicMock()
    if exc is not None:
        session.get.side_effect = exc
    else:
        session.get.return_value = resp
    return session


def _resp(status=200, payload=None, json_raises=False):
    resp = MagicMock()
    resp.status_code = status
    if json_raises:
        resp.json.side_effect = ValueError("bad json")
    else:
        resp.json.return_value = payload if payload is not None else {}
    return resp


def test_fetch_success():
    session = _session(_resp(200, _payload()))
    m = mf.fetch_manifest("2.6.0", session=session, backoff=0.0)
    assert m is not None and m.version == "2.6.1"
    assert session.get.call_count == 1


def test_fetch_no_update_returns_none():
    session = _session(_resp(200, _payload()))
    assert mf.fetch_manifest("2.6.1", session=session, backoff=0.0) is None


def test_fetch_404_is_failed_check_not_no_update():
    session = _session(_resp(404))
    with pytest.raises(UpdateError) as ei:
        mf.fetch_manifest("2.6.0", session=session, backoff=0.0)
    assert ei.value.code is UpdateErrorCode.HTTP_ERROR


def test_fetch_5xx_retries_then_raises():
    session = _session(_resp(502))
    with pytest.raises(UpdateError) as ei:
        mf.fetch_manifest("2.6.0", session=session, retries=2, backoff=0.0)
    assert ei.value.code is UpdateErrorCode.HTTP_ERROR
    assert session.get.call_count == 3  # 1 + 2 retries


def test_fetch_5xx_recovers_on_retry():
    session = MagicMock()
    session.get.side_effect = [_resp(502), _resp(200, _payload())]
    m = mf.fetch_manifest("2.6.0", session=session, backoff=0.0)
    assert m is not None


def test_fetch_network_error():
    session = _session(exc=requests.ConnectionError("reset"))
    with pytest.raises(UpdateError) as ei:
        mf.fetch_manifest("2.6.0", session=session, retries=1, backoff=0.0)
    assert ei.value.code is UpdateErrorCode.NETWORK_ERROR
    assert session.get.call_count == 2


def test_fetch_malformed_json_is_permanent():
    session = _session(_resp(200, json_raises=True))
    with pytest.raises(UpdateError) as ei:
        mf.fetch_manifest("2.6.0", session=session, retries=3, backoff=0.0)
    assert ei.value.code is UpdateErrorCode.MANIFEST_INVALID
    assert session.get.call_count == 1  # no retry for a bad manifest
