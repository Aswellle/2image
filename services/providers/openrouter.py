"""
services/providers/openrouter.py
OpenRouter 图像生成 — 部分模型免费（如 opengvlab/internvl3-14b:free）
端点: POST https://openrouter.ai/api/v1/chat/completions
认证: Bearer Token
请求关键字段: modalities: ["image"] 或 ["image","text"]
响应: choices[0].message.content[].image_url.url  |  .data (base64)
"""

import base64
import threading
import time
from typing import Callable, Tuple
import ipaddress
from urllib.parse import urlparse

import requests
# Session with connection pooling for HTTP keep-alive
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(
    pool_connections=2, pool_maxsize=4, max_retries=1)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)


PROVIDER_INFO = {
    "name": "OpenRouter (部分免费)",
    "category": "free",
    "config_key": "openrouter_key",
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

# ── 串行锁 ────────────────────────────────────────────────────────────
_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 3.0  # OpenRouter 免费模型限速较严

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell:free"
_TIMEOUT = 120
_MAX_RETRIES = 3


def try_openrouter(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("openrouter_key", "").strip()
    if not key:
        raise ValueError(
            "需要 OpenRouter API Key！注册：https://openrouter.ai/keys"
        )

    model = cfg.get("openrouter_model", "").strip() or _DEFAULT_MODEL

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/local/text-to-image-app",
        "X-Title": "TextToImageApp",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "modalities": ["image"],
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[OpenRouter] 尝试 {attempt}/{_MAX_RETRIES}，模型：{model}…")
                resp = _session.post(
                    _ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=_TIMEOUT,
                )
                if resp.status_code == 429:
                    log("[OpenRouter] 速率限制，等待 30s…")
                    time.sleep(30)
                    continue
                if resp.status_code == 402:
                    raise ValueError("OpenRouter 余额不足，请充值或更换免费模型。")
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {_safe_error_text(resp)}"
                    )

                data = resp.json()
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log(f"[OpenRouter] 生成成功 ✓ 模型：{model}")
                return (image_bytes, f"OpenRouter/{model.split('/')[-1]}")

            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[OpenRouter] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(4 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                log(f"[OpenRouter] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(4 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"OpenRouter 全部重试失败：{last_err}")


def _extract_image(data: dict, log: Callable) -> bytes:
    """
    兼容两种响应格式：
    1. content 为列表：[{"type":"image_url","image_url":{"url":"..."}}]
    2. content 为字符串（直接 URL）
    """
    choices = data.get("choices", [])
    if not choices:
        raise ValueError(f"OpenRouter 响应无 choices：{data}")

    message = choices[0].get("message", {})
    content = message.get("content", "")

    # 格式1：content 是列表
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                img_url_obj = item.get("image_url", {})
                url = img_url_obj.get("url", "") if isinstance(img_url_obj, dict) else img_url_obj
                if url:
                    return _fetch_or_decode(url, log)
                # 也可能直接在 data 字段
                data_b64 = item.get("data", "")
                if data_b64:
                    return base64.b64decode(data_b64)

    # 格式2：content 是字符串 URL
    if isinstance(content, str) and content.strip():
        return _fetch_or_decode(content.strip(), log)

    raise ValueError(f"OpenRouter 响应中未找到图片，message={message}")


def _fetch_or_decode(url_or_b64: str, log: Callable) -> bytes:
    """判断是 URL 还是 base64 data URI，并返回图片字节。"""
    if url_or_b64.startswith("data:"):
        # data URI: data:image/png;base64,xxxx
        _, b64_part = url_or_b64.split(",", 1)
        return base64.b64decode(b64_part)

    parsed = urlparse(url_or_b64)
    if parsed.scheme in ("http", "https"):
        log(f"[OpenRouter] 下载图片：{url_or_b64[:80]}…")
        if not _validate_image_url(url_or_b64):
            raise RuntimeError(f"Blocked unsafe image URL: {url_or_b64[:100]}")
        r = _session.get(url_or_b64, timeout=60)
        r.raise_for_status()
        return r.content

    # 最后尝试当作纯 base64
    try:
        return base64.b64decode(url_or_b64)
    except Exception:
        raise ValueError(f"无法解析图片来源：{url_or_b64[:80]}")
