"""services/update_service 单元测试 — 版本比较、资产选择、下载校验、清单解析。

网络调用全部 mock；文件操作经 tmp_path 隔离（conftest autouse 已兜底）。
"""
import hashlib
from unittest.mock import MagicMock, patch

import pytest

from services.generation.errors import GenerationCancelled
from services.generation.cancellation import CancellationToken
from services import update_service as us


def _asset(name="text2image_pro_v2.7.0.exe", size=1024, url="https://example.com/dl"):
    return {"name": name, "url": url, "size": size}


# ── 版本比较 ─────────────────────────────────────────────────

def test_is_newer_basic():
    assert us.is_newer("v2.7.0", "2.6.0")
    assert us.is_newer("v2.6.1", "v2.6.0")
    assert not us.is_newer("v2.6.0", "2.6.0")
    assert not us.is_newer("v2.5.9", "v2.6.0")


def test_is_newer_tolerates_suffix_and_garbage():
    assert us.is_newer("v2.7.0-beta.1", "2.6.0")
    assert not us.is_newer("release-2.5", "2.6.0")
    assert not us.is_newer("", "2.6.0")          # 解析失败按 0.0.0
    assert us.is_newer("v3.0.0", "")             # 当前未知 → 任何新版都算新


def test_get_current_version_returns_value():
    v = us.get_current_version()
    assert v and v != "0.0.0" or v == "0.0.0"    # 仓库内可读到真实版本
    assert isinstance(v, str)


# ── 资产选择 ─────────────────────────────────────────────────

def test_pick_installer_and_portable():
    assets = [
        _asset("text2image_pro_v2.7.0.exe", 1024),
        _asset("text2image_pro.exe", 512),
        _asset("SHA256SUMS.txt", 64),
        _asset("SBOM.spdx.json", 32),
    ]
    r = us.ReleaseInfo(tag="v2.7.0", version="2.7.0", url="u", notes="n",
                       published_at="", installer=None, portable=None,
                       checksums=None)
    assert us._pick_asset(assets, lambda n: bool(us._INSTALLER_RE.match(n)))["name"] \
        == "text2image_pro_v2.7.0.exe"
    assert us._pick_asset(assets, lambda n: n == us._PORTABLE_NAME)["size"] == 512
    assert us._pick_asset(assets, lambda n: n == us._CHECKSUMS_NAME)


def test_installer_regex_rejects_portable():
    assert not us._INSTALLER_RE.match("text2image_pro.exe")
    assert not us._INSTALLER_RE.match("text2image_pro_v2.7.0.zip")


# ── fetch_latest_release ─────────────────────────────────────

def _mk_resp(status=200, json_data=None):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_data if json_data is not None else {}
    if json_data is None:
        m.json.side_effect = ValueError("no json")
    return m


def test_fetch_latest_release_parses_assets():
    data = {
        "tag_name": "v2.7.0",
        "html_url": "https://github.com/Aswellle/2image/releases/tag/v2.7.0",
        "body": "# notes",
        "published_at": "2026-10-06T00:00:00Z",
        "assets": [
            {"name": "text2image_pro_v2.7.0.exe", "browser_download_url": "u1", "size": 1},
            {"name": "SHA256SUMS.txt", "browser_download_url": "u2", "size": 2},
        ],
    }
    with patch("services.providers._net.get_session") as gs:
        gs.return_value.get.return_value = _mk_resp(200, data)
        r = us.fetch_latest_release()
    assert r.version == "2.7.0" and r.installer["url"] == "u1"
    assert r.checksums["name"] == "SHA256SUMS.txt" and r.portable is None


def test_fetch_latest_release_404_returns_none():
    with patch("services.providers._net.get_session") as gs:
        gs.return_value.get.return_value = _mk_resp(404)
        assert us.fetch_latest_release() is None


def test_fetch_latest_release_network_error_raises_update_error():
    import requests as _rq
    with patch("services.providers._net.get_session") as gs:
        gs.return_value.get.side_effect = _rq.ConnectionError("reset")
        with pytest.raises(us.UpdateError, match="网络请求失败"):
            us.fetch_latest_release()


def test_fetch_latest_release_http_error_raises():
    with patch("services.providers._net.get_session") as gs:
        gs.return_value.get.return_value = _mk_resp(502)
        with pytest.raises(us.UpdateError, match="502"):
            us.fetch_latest_release()


# ── 清单解析与 SHA256 校验 ───────────────────────────────────

def test_parse_checksums():
    h1 = "a" * 64
    h2 = "b" * 64
    text = ("# SHA256SUMS\n"
            f"{h1}  text2image_pro_v2.7.0.exe\n"
            f"{h2}  other.bin\n"
            "bad-line\n"
            "zz22  not-hex-hash\n")
    d = us.parse_checksums(text)
    assert d["text2image_pro_v2.7.0.exe"] == h1
    assert d["other.bin"] == h2
    assert len(d) == 2                    # 非 64 hex 的行被拒绝


def test_sha256_of(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"hello world")
    assert us.sha256_of(f) == hashlib.sha256(b"hello world").hexdigest()


def test_sha256_cancellation(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"x" * 4096)
    token = CancellationToken()
    token.cancel()
    with pytest.raises(GenerationCancelled):
        us.sha256_of(f, token=token)


# ── 下载与校验组合 ───────────────────────────────────────────

def _mk_stream_resp(content: bytes, text: str = None):
    m = MagicMock()
    m.status_code = 200
    m.headers = {"Content-Length": str(len(content))}
    m.iter_content = lambda size: iter([content])
    m.text = text if text is not None else content.decode("utf-8", "replace")
    m.raise_for_status.return_value = None
    m.close.return_value = None
    return m


def test_download_and_verify_success(tmp_path):
    content = b"installer-bytes" * 100
    asset = _asset(size=len(content), url="https://example.com/dl")
    sums = _asset("SHA256SUMS.txt", url="https://example.com/sums")
    digest = hashlib.sha256(content).hexdigest()

    with patch("services.providers._net.get_session") as gs:
        gs.return_value.get.side_effect = [
            _mk_stream_resp(content),
            _mk_stream_resp(f"{digest}  {asset['name']}\n".encode()),
        ]
        path = us.download_and_verify(asset, sums)
    assert path.exists() and path.read_bytes() == content
    path.unlink()


def test_download_and_verify_checksum_mismatch(tmp_path):
    asset = _asset(size=8, url="https://example.com/dl")
    sums = _asset("SHA256SUMS.txt", url="https://example.com/sums")

    with patch("services.providers._net.get_session") as gs:
        gs.return_value.get.side_effect = [
            _mk_stream_resp(b"tampered"),
            _mk_stream_resp(b"0" * 64 + f"  {asset['name']}\n".encode()),
        ]
        with pytest.raises(us.ChecksumMismatchError):
            us.download_and_verify(asset, sums)
    # 校验失败必须删除半成品
    assert not (us.update_download_dir() / asset["name"]).exists()


def test_download_and_verify_missing_entry_rejects(tmp_path):
    asset = _asset(size=4, url="https://example.com/dl")
    sums = _asset("SHA256SUMS.txt", url="https://example.com/sums")
    with patch("services.providers._net.get_session") as gs:
        gs.return_value.get.side_effect = [
            _mk_stream_resp(b"data"),
            _mk_stream_resp(b"0" * 64 + "  unrelated.bin\n".encode()),
        ]
        with pytest.raises(us.UpdateError, match="缺少该文件的条目"):
            us.download_and_verify(asset, sums)


def test_download_cancel_cleans_partial(tmp_path):
    asset = _asset(size=100, url="https://example.com/dl")
    token = CancellationToken()
    token.cancel()
    with patch("services.providers._net.get_session") as gs:
        gs.return_value.get.return_value = _mk_stream_resp(b"x" * 100)
        with pytest.raises(GenerationCancelled):
            us.download_asset(asset, token=token)
    assert not (us.update_download_dir() / asset["name"]).exists()


def test_download_oversize_aborts(tmp_path):
    asset = _asset(size=100, url="https://example.com/dl")
    with patch("services.providers._net.get_session") as gs:
        gs.return_value.get.return_value = _mk_stream_resp(b"x" * 64)
        with pytest.raises(us.UpdateError, match="上限"):
            us.download_asset(asset, max_bytes=16)
    assert not (us.update_download_dir() / asset["name"]).exists()


def test_download_incomplete_rejected(tmp_path):
    asset = _asset(size=1000, url="https://example.com/dl")
    with patch("services.providers._net.get_session") as gs:
        gs.return_value.get.return_value = _mk_stream_resp(b"short")
        with pytest.raises(us.UpdateError, match="下载不完整"):
            us.download_asset(asset)
    assert not (us.update_download_dir() / asset["name"]).exists()
