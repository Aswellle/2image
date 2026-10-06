"""Download + integrity gate tests (§28.2): .partial lifecycle, size and
SHA-256 verification, retry, cancellation cleanup, reuse, allowlist."""
import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from services.generation.cancellation import CancellationToken
from services.generation.errors import GenerationCancelled
from services.updater import downloader as dl
from services.updater.errors import ChecksumMismatchError, UpdateError, UpdateErrorCode
from services.updater.manifest import UpdateAsset

CONTENT = b"installer-payload-" * 512          # 8704 bytes
SHA = hashlib.sha256(CONTENT).hexdigest()
URL = ("https://github.com/Aswellle/2image/releases/download/v2.7.0/"
       "2image-setup-v2.7.0.exe")


def _asset(size=None, sha=None, url=URL):
    return UpdateAsset("2image-setup-v2.7.0.exe", url,
                       len(CONTENT) if size is None else size,
                       SHA if sha is None else sha)


def _stream_resp(chunks, final_url=URL, content_length=None):
    resp = MagicMock()
    if chunks is not None:
        resp.iter_content.return_value = iter(chunks)
    resp.url = final_url
    headers = {}
    if content_length is not None:
        headers["Content-Length"] = str(content_length)
    resp.headers = headers
    resp.close = MagicMock()
    return resp


def _session(resp):
    session = MagicMock()
    session.get.return_value = resp
    return session


def _track_session(resp, cancel_after=None, token=None):
    """Session whose stream cancels the token mid-download when asked."""
    def _chunks():
        for i, chunk in enumerate(chunks_iter):
            if cancel_after is not None and i == cancel_after and token:
                token.cancel()
            yield chunk
    chunks_iter = [CONTENT[:1000], CONTENT[1000:2000], CONTENT[2000:]]
    resp.iter_content.return_value = _chunks()
    return _session(resp)


# ── happy path ───────────────────────────────────────────────

def test_success_writes_final_no_partial(tmp_path):
    session = _session(_stream_resp([CONTENT]))
    path = dl.download_verified(_asset(), tmp_path, session=session)
    assert path.name == "2image-setup-v2.7.0.exe"
    assert path.read_bytes() == CONTENT
    assert not Path(str(path) + ".partial").exists()


def test_progress_reports_download_and_verify(tmp_path):
    session = _session(_stream_resp([CONTENT[:100], CONTENT[100:]]))
    stages = []
    dl.download_verified(_asset(), tmp_path, session=session,
                         progress=lambda s, d, t, sp: stages.append(s))
    assert "download" in stages and "verify" in stages


def test_existing_verified_file_is_reused(tmp_path):
    final = tmp_path / "2image-setup-v2.7.0.exe"
    final.write_bytes(CONTENT)
    session = MagicMock()
    path = dl.download_verified(_asset(), tmp_path, session=session)
    assert path == final
    session.get.assert_not_called()          # no second download


# ── integrity gate ───────────────────────────────────────────

def test_size_mismatch_rejects_and_cleans(tmp_path):
    # stream delivers MORE bytes than the manifest declared
    session = _session(_stream_resp([CONTENT]))
    with pytest.raises(UpdateError) as ei:
        dl.download_verified(_asset(size=len(CONTENT) - 1), tmp_path,
                             session=session)
    assert ei.value.code is UpdateErrorCode.SIZE_MISMATCH
    assert list(tmp_path.iterdir()) == []    # nothing left behind


def test_hash_mismatch_rejects_and_cleans(tmp_path):
    session = _session(_stream_resp([CONTENT]))
    with pytest.raises(ChecksumMismatchError):
        dl.download_verified(_asset(sha="b" * 64), tmp_path, session=session)
    assert list(tmp_path.iterdir()) == []


def test_incomplete_stream_retries_then_fails(tmp_path):
    truncated = CONTENT[:100]
    session = MagicMock()
    session.get.return_value = _stream_resp([truncated])
    with pytest.raises(UpdateError) as ei:
        dl.download_verified(_asset(), tmp_path, session=session,
                             retries=2, backoff=0.0)
    assert ei.value.code is UpdateErrorCode.DOWNLOAD_FAILED
    assert session.get.call_count == 3
    assert list(tmp_path.iterdir()) == []


def test_recovers_on_retry(tmp_path):
    session = MagicMock()
    session.get.side_effect = [
        _stream_resp([CONTENT[:10]]),
        _stream_resp([CONTENT]),
    ]
    path = dl.download_verified(_asset(), tmp_path, session=session,
                                backoff=0.0)
    assert path.read_bytes() == CONTENT


def test_max_bytes_cap(tmp_path):
    session = _session(_stream_resp([CONTENT]))
    with pytest.raises(UpdateError) as ei:
        dl.download_verified(_asset(), tmp_path, session=session,
                             max_bytes=10)
    assert ei.value.code is UpdateErrorCode.SIZE_MISMATCH


# ── cancellation ─────────────────────────────────────────────

def test_cancel_mid_stream_cleans_partial(tmp_path):
    token = CancellationToken()
    session = _track_session(_stream_resp(None), cancel_after=1, token=token)
    with pytest.raises(GenerationCancelled):
        dl.download_verified(_asset(), tmp_path, token=token, session=session)
    assert list(tmp_path.iterdir()) == []


# ── URL allowlist (defense in depth) ────────────────────────

def test_rejects_non_allowlisted_url(tmp_path):
    with pytest.raises(UpdateError) as ei:
        dl.download_verified(_asset(url="https://evil.example/x.exe"),
                             tmp_path, session=MagicMock())
    assert ei.value.code is UpdateErrorCode.MANIFEST_INVALID


def test_rejects_redirect_off_allowlist(tmp_path):
    session = _session(_stream_resp([CONTENT],
                                    final_url="https://evil.example/bin"))
    with pytest.raises(UpdateError) as ei:
        dl.download_verified(_asset(), tmp_path, session=session)
    assert ei.value.code is UpdateErrorCode.MANIFEST_INVALID


# ── sha256 helper ────────────────────────────────────────────

def test_sha256_file_matches_hashlib(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(CONTENT)
    assert dl.sha256_file(p) == SHA


def test_network_error_wraps_and_retries(tmp_path):
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("reset")
    with pytest.raises(UpdateError) as ei:
        dl.download_verified(_asset(), tmp_path, session=session,
                             retries=1, backoff=0.0)
    assert ei.value.code is UpdateErrorCode.DOWNLOAD_FAILED
    assert session.get.call_count == 2
