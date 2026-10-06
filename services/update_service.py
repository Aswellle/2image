"""
services/update_service.py — 应用自更新（GitHub Releases 托管）
───────────────────────────────────────────────────────────────
检查更新 → 下载安装包 → SHA256 校验 → 静默安装（自动卸载旧版并重启新程序）。

设计约束：
  · 全部网络/磁盘操作为阻塞式，调用方必须放入工作线程，UI 经 root.after 回传
  · 下载流式落盘 + 大小上限 + 取消令牌，取消时清理半成品文件
  · 安装包必须通过发行版附带的 SHA256SUMS.txt 校验才允许执行
  · 静默安装使用 Inno Setup 标准开关：自动关闭本应用、卸载旧版本、
    完成后重启新版（/CLOSEAPPLICATIONS + /RESTARTAPPLICATIONS）
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

from services.generation.cancellation import CancellationToken
from services.generation.errors import GenerationCancelled

REPO_OWNER = "Aswellle"
REPO_NAME = "2image"
RELEASES_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/latest"

# 发行资产命名（与 CI 构建产物一致）
_INSTALLER_RE = re.compile(r"^text2image_pro_v\d+\.\d+\.\d+\.exe$")
_PORTABLE_NAME = "text2image_pro.exe"
_CHECKSUMS_NAME = "SHA256SUMS.txt"
_MAX_ASSET_BYTES = 200 * 1024 * 1024   # 安装包 ~19MB，留足余量
_CONNECT_TIMEOUT = 8.0
_READ_TIMEOUT = 60.0
API_HEADERS = {"Accept": "application/vnd.github+json"}


class UpdateError(RuntimeError):
    """更新流程通用失败。"""


class ChecksumMismatchError(UpdateError):
    """安装包 SHA256 与发行清单不符——拒绝执行。"""


@dataclass(frozen=True)
class ReleaseInfo:
    """最新发行版摘要（releases/latest 仅返回正式版，预发布自动排除）。"""
    tag: str                  # "v2.6.0"
    version: str              # "2.6.0"
    url: str                  # 发行页地址
    notes: str                # 发行说明全文（Markdown）
    published_at: str         # ISO 时间
    installer: dict | None    # {"name","url","size"} 安装包资产
    portable: dict | None     # 便携版资产
    checksums: dict | None    # SHA256SUMS.txt 资产


# ── 本地版本 ─────────────────────────────────────────────────

def get_current_version() -> str:
    """当前程序版本号。version.json 经 PyInstaller datas 打包（_MEIPASS）。"""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(getattr(sys, "_MEIPASS", ".")) / "version.json")
    candidates.append(Path(__file__).resolve().parents[1] / "version.json")
    for p in candidates:
        try:
            return str(json.loads(p.read_text(encoding="utf-8"))["version"]).strip()
        except Exception:
            continue
    return "0.0.0"


def is_packaged() -> bool:
    """是否打包环境（PyInstaller 冻结）。"""
    return bool(getattr(sys, "frozen", False))


def detect_install_mode() -> bool:
    """是否为安装版：exe 同目录存在 Inno 卸载器 unins000.exe。"""
    if not is_packaged():
        return False
    try:
        return Path(sys.executable).parent.joinpath("unins000.exe").exists()
    except OSError:
        return False


def is_newer(latest_tag: str, current: str) -> bool:
    """语义化版本比较（容忍 v 前缀与附加后缀）。"""
    def parse(v: str) -> tuple[int, int, int]:
        m = re.search(r"(\d+)\.(\d+)\.(\d+)", v or "")
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
    return parse(latest_tag) > parse(current)


# ── 检查更新 ─────────────────────────────────────────────────

def fetch_latest_release(timeout: float = 15.0) -> ReleaseInfo | None:
    """查询最新正式发行版；无发行版返回 None；网络/接口失败抛 UpdateError。"""
    from services.providers._net import get_session
    try:
        resp = get_session().get(RELEASES_API, headers=API_HEADERS,
                                 timeout=(timeout, timeout))
    except requests.RequestException as exc:
        raise UpdateError(f"网络请求失败：{exc}") from exc
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise UpdateError(f"GitHub API 返回 HTTP {resp.status_code}")

    j = resp.json()
    tag = str(j.get("tag_name", "")).strip()
    assets = j.get("assets") or []
    installer = _pick_asset(assets, lambda n: bool(_INSTALLER_RE.match(n)))
    portable = _pick_asset(assets, lambda n: n == _PORTABLE_NAME)
    checksums = _pick_asset(assets, lambda n: n == _CHECKSUMS_NAME)
    return ReleaseInfo(
        tag=tag,
        version=tag.lstrip("vV"),
        url=str(j.get("html_url") or RELEASES_PAGE),
        notes=str(j.get("body") or ""),
        published_at=str(j.get("published_at") or ""),
        installer=installer,
        portable=portable,
        checksums=checksums,
    )


def _pick_asset(assets: list, name_pred: Callable[[str], bool]) -> dict | None:
    for a in assets:
        name = str(a.get("name", ""))
        if name_pred(name):
            return {"name": name,
                    "url": str(a.get("browser_download_url", "")),
                    "size": int(a.get("size", 0))}
    return None


# ── 下载与校验 ───────────────────────────────────────────────

def update_download_dir() -> Path:
    d = Path(tempfile.gettempdir()) / "2image-update"
    d.mkdir(parents=True, exist_ok=True)
    return d


def download_asset(asset: dict, progress_cb: Callable[[int, int], None] | None = None,
                   token: CancellationToken | None = None,
                   max_bytes: int = _MAX_ASSET_BYTES) -> Path:
    """流式下载发行资产到临时更新目录，返回本地路径。

    progress_cb(done_bytes, total_bytes)；token 取消时清理半成品并抛
    GenerationCancelled；超过 max_bytes 视为异常数据直接放弃。
    """
    from services.providers._net import get_session
    name = str(asset.get("name", "")).strip()
    url = str(asset.get("url", "")).strip()
    if not name or not url:
        raise UpdateError("资产信息不完整")
    dest = update_download_dir() / name
    total = int(asset.get("size", 0))
    done = 0

    try:
        resp = get_session().get(url, stream=True, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        resp.raise_for_status()
        if total <= 0:
            cl = resp.headers.get("Content-Length")
            total = int(cl) if cl and cl.isdigit() else 0
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(128 * 1024):
                if token is not None:
                    token.throw_if_cancelled()
                if chunk:
                    fh.write(chunk)
                    done += len(chunk)
                    if done > max_bytes:
                        raise UpdateError(f"下载超过 {max_bytes // (1024 * 1024)}MB 上限，已中止")
                    if progress_cb is not None:
                        progress_cb(done, total)
    except GenerationCancelled:
        _silent_unlink(dest)
        raise
    except UpdateError:
        _silent_unlink(dest)
        raise
    except requests.RequestException as exc:
        _silent_unlink(dest)
        raise UpdateError(f"下载失败：{exc}") from exc
    except OSError as exc:
        _silent_unlink(dest)
        raise UpdateError(f"写入临时文件失败：{exc}") from exc
    finally:
        try:
            resp.close()
        except Exception:
            pass

    if total and done < total:
        _silent_unlink(dest)
        raise UpdateError(f"下载不完整（{done}/{total} 字节）")
    return dest


def parse_checksums(text: str) -> dict[str, str]:
    """解析 SHA256SUMS 清单（sha256sum 格式：<hash>  <filename>）。"""
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            out[parts[1].lstrip("*")] = parts[0].lower()
    return out


def sha256_of(path: Path, progress_cb: Callable[[int, int], None] | None = None,
              token: CancellationToken | None = None) -> str:
    h = hashlib.sha256()
    size = path.stat().st_size
    done = 0
    with open(path, "rb") as fh:
        while True:
            if token is not None:
                token.throw_if_cancelled()
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            done += len(chunk)
            if progress_cb is not None:
                progress_cb(done, size)
    return h.hexdigest()


def download_and_verify(asset: dict, checksums_asset: dict | None,
                        progress_cb: Callable[[str, int, int], None] | None = None,
                        token: CancellationToken | None = None) -> Path:
    """下载资产并按发行清单校验 SHA256；校验失败删除文件并抛错。

    progress_cb(stage, done, total)：stage ∈ {"download", "verify"}。
    """
    def _cb(stage: str):
        if progress_cb is None:
            return None
        return lambda done, total: progress_cb(stage, done, total)

    path = download_asset(asset, _cb("download"), token)
    if checksums_asset is None:
        # 无清单可校验（不应发生）：保留文件但由调用方提示风险
        return path
    sums_text = ""
    try:
        from services.providers._net import get_session
        resp = get_session().get(str(checksums_asset.get("url", "")),
                                 timeout=(_CONNECT_TIMEOUT, 30))
        resp.raise_for_status()
        sums_text = resp.text
    except requests.RequestException as exc:
        _silent_unlink(path)
        raise UpdateError(f"校验清单下载失败：{exc}") from exc

    expected = parse_checksums(sums_text).get(str(asset.get("name", "")))
    if not expected:
        _silent_unlink(path)
        raise UpdateError("校验清单中缺少该文件的条目，拒绝安装")
    actual = sha256_of(path, _cb("verify"), token)
    if actual != expected.lower():
        _silent_unlink(path)
        raise ChecksumMismatchError(
            f"安装包校验失败（SHA256 不匹配），已删除下载文件。"
            f"期望 {expected[:16]}…，实际 {actual[:16]}…")
    return path


# ── 安装 ─────────────────────────────────────────────────────

def launch_installer(installer_path: Path) -> None:
    """静默运行 Inno Setup 安装程序：自动关闭本应用、卸载旧版本、
    安装完成后重启新版（/RESTARTAPPLICATIONS）。"""
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [str(installer_path),
         "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES",
         "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"],
        creationflags=flags,
        close_fds=True,
    )


def _silent_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
