"""
services/providers/recraft.py — Recraft v3
设计/插画/品牌VI首选，OpenAI 兼容接口，支持写实/插画/矢量多风格。
API: POST https://external.api.recraft.ai/v1/images/generations
Key: Header  Authorization: Bearer <key>

风格(recraft_style)可选值：
  realistic_image      — 写实摄影（默认，适合商业图）
  digital_illustration — 数字插画（适合小红书/封面）
  vector_illustration  — 矢量插画（适合品牌/图标）
"""
import base64
import threading
import time
import requests
# Session with connection pooling for HTTP keep-alive
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(
    pool_connections=2, pool_maxsize=4, max_retries=1)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

import ipaddress
from urllib.parse import urlparse
from typing import Callable, Tuple

PROVIDER_INFO = {
    "name": "Recraft v3 (设计/插画)",
    "category": "commercial",
    "config_key": "recraft_key",
}


def _validate_image_url(url: str) -> bool:
    """Block non-HTTPS URLs and internal/reserved IP ranges to prevent SSRF."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("https",):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            return False
    except ValueError:
        pass
    return True


def _safe_error_text(resp) -> str:
    """Extract safe error message from API response, avoiding raw body leakage."""
    try:
        body = resp.json()
        err = body.get("error", {})
        if isinstance(err, dict):
            return err.get("message", "") or str(err)[:150]
        if isinstance(err, str):
            return err[:150]
        return body.get("message", "") or str(body)[:150]
    except Exception:
        return f"HTTP {resp.status_code}"
_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0

# 支持的输出尺寸（选最接近的）
_SIZES = [
    ((1024, 1024), "1024x1024"),
    ((1365, 1024), "1365x1024"),
    ((1024, 1365), "1024x1365"),
    ((1536, 1024), "1536x1024"),
    ((1024, 1536), "1024x1536"),
    ((1820, 1024), "1820x1024"),
    ((1024, 1820), "1024x1820"),
]


def _best_size(w: int, h: int) -> str:
    r = w / max(h, 1)
    return min(_SIZES, key=lambda x: abs(x[0][0] / x[0][1] - r))[1]


def try_recraft(prompt: str, w: int, h: int, seed: int,
                cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("recraft_key", "").strip()
    if not key:
        raise ValueError("需要 Recraft API Key！注册：https://www.recraft.ai/")

    size  = _best_size(w, h)
    style = cfg.get("recraft_style", "realistic_image")
    log(f"► Recraft v3  尺寸={size}  风格={style}")

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _session.post(
                "https://external.api.recraft.ai/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "prompt": prompt,
                    "style":  style,
                    "n":      1,
                    "size":   size,
                    "model":  "recraftv3",
                },
                timeout=120,
            )
        except requests.exceptions.ConnectionError as e:
            _LAST_DONE[0] = time.time()
            raise ValueError(f"无法连接 Recraft: {e}")
        _LAST_DONE[0] = time.time()

    log(f"  状态: {resp.status_code}")
    if resp.status_code == 401:
        raise ValueError("Recraft API Key 无效")
    if resp.status_code == 429:
        raise ValueError("Recraft 速率限制")
    if resp.status_code != 200:
        raise ValueError(f"Recraft 返回 {resp.status_code}: {_safe_error_text(resp)}")

    data = resp.json().get("data", [])
    if not data:
        raise ValueError("Recraft 返回数据为空")

    img_url = data[0].get("url", "")
    if img_url:
        if not _validate_image_url(img_url):
            raise RuntimeError(f"Blocked unsafe image URL: {img_url[:100]}")
        ir = _session.get(img_url, timeout=60)
        ir.raise_for_status()
        log(f"  ✓ Recraft v3 成功（URL）{len(ir.content) // 1024}KB")
        return ir.content, f"Recraft/v3-{style}"

    b64 = data[0].get("b64_json", "")
    if b64:
        img = base64.b64decode(b64)
        log(f"  ✓ Recraft v3 成功（base64）{len(img) // 1024}KB")
        return img, f"Recraft/v3-{style}"

    raise ValueError("Recraft 响应中无图片数据")
