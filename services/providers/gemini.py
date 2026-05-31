"""
services/providers/gemini.py
Google Gemini 2.5 Flash Image — 免费 500 次/天
端点: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent
认证: Header x-goog-api-key
响应: candidates[0].content.parts[].inlineData.data  (base64 PNG)
"""

import base64
import threading
import time
from typing import Callable, Tuple

import requests
# Session with connection pooling for HTTP keep-alive
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(
    pool_connections=2, pool_maxsize=4, max_retries=1)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)


PROVIDER_INFO = {
    "name": "Google Gemini (免费500次/天)",
    "category": "free",
    "config_key": "gemini_key",
}


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

# ── 串行锁（防批量变体并发触发速率限制）──────────────────────────────
_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 2.0  # Gemini 免费层建议间隔

_MODEL = "gemini-2.5-flash-preview-04-17"
_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{_MODEL}:generateContent"
)
_TIMEOUT = 90
_MAX_RETRIES = 3


def try_gemini(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("gemini_key", "").strip()
    if not key:
        raise ValueError("需要 Google Gemini API Key！注册：https://aistudio.google.com/")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    }
    # Gemini generateContent 图像生成请求体
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
        },
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Gemini] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = _session.post(
                    _ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=_TIMEOUT,
                )
                if resp.status_code == 429:
                    log("[Gemini] 触发速率限制，等待 30s…")
                    time.sleep(30)
                    continue
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {_safe_error_text(resp)}"
                    )

                data = resp.json()
                # 解析 base64 图片数据
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log("[Gemini] 生成成功 ✓")
                return (image_bytes, "Gemini/2.5-Flash-Image")

            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[Gemini] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                log(f"[Gemini] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Gemini 全部重试失败：{last_err}")


def _extract_image(data: dict, log: Callable) -> bytes:
    """从 Gemini 响应中提取 base64 图片数据并解码。"""
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini 响应无 candidates（格式异常）")

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        inline = part.get("inlineData", {})
        b64 = inline.get("data", "")
        if b64:
            try:
                return base64.b64decode(b64)
            except Exception as e:
                raise ValueError(f"base64 解码失败：{e}")

    raise ValueError("Gemini 响应中未找到图片数据")
