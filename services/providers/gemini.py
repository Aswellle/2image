"""
services/providers/gemini.py
Google Gemini 2.5 Flash Image — 免费 500 次/天
端点: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent
认证: Header x-goog-api-key
响应: candidates[0].content.parts[].inlineData.data (base64 PNG)
"""
import base64, threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0
_MODEL     = "gemini-2.5-flash-preview-04-17"
_ENDPOINT  = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:generateContent"
_TIMEOUT  = 90
_MAX_RETRIES = 3


def try_gemini(
    prompt: str, w: int, h: int, seed: int,
    cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("gemini_key", "").strip()
    if not key:
        raise ValueError("需要 Google Gemini API Key！注册：https://aistudio.google.com/")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Gemini] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = requests.post(
                    _ENDPOINT, headers=headers, json=payload, timeout=_TIMEOUT
                )
                if resp.status_code == 429:
                    log("[Gemini] 速率限制，等待 30s…")
                    time.sleep(30); continue
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

                data = resp.json()
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log("[Gemini] 生成成功 ✓")
                return (image_bytes, "Gemini/2.5-Flash-Image")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Gemini] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[Gemini] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Gemini 全部重试失败：{last_err}")


def _extract_image(data: dict, log: Callable) -> bytes:
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError(f"Gemini 响应无 candidates：{data}")
    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        inline = part.get("inlineData", {})
        b64 = inline.get("data", "")
        if b64:
            return base64.b64decode(b64)
    raise ValueError(f"Gemini 响应中未找到图片数据，parts={parts}")
