"""
services/providers/openrouter.py
OpenRouter 图像生成 — 聚合 16+ 模型，部分免费
端点: POST https://openrouter.ai/api/v1/chat/completions
认证: Bearer Token
请求: modalities: ["image"]
响应: choices[0].message.content[].image_url.url | data (base64)
"""
import base64, threading, time
from typing import Callable, Tuple
from urllib.parse import urlparse
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 3.0
_ENDPOINT  = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell:free"
_TIMEOUT  = 120
_MAX_RETRIES = 3


def try_openrouter(
    prompt: str, w: int, h: int, seed: int,
    cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("openrouter_key", "").strip()
    if not key:
        raise ValueError("需要 OpenRouter API Key！注册：https://openrouter.ai/keys")

    model = cfg.get("openrouter_model", "").strip() or _DEFAULT_MODEL

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/Aswellle/2image",
        "X-Title": "2image",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image"],
    }
    if seed and seed > 0:
        payload["seed"] = seed

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[OpenRouter] 尝试 {attempt}/{_MAX_RETRIES}，模型：{model}…")
                resp = requests.post(
                    _ENDPOINT, headers=headers, json=payload, timeout=_TIMEOUT
                )
                if resp.status_code == 429:
                    log("[OpenRouter] 速率限制，等待 30s…")
                    time.sleep(30); continue
                if resp.status_code == 402:
                    raise ValueError("OpenRouter 余额不足，请充值或更换免费模型。")
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

                data = resp.json()
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log(f"[OpenRouter] 生成成功 ✓ 模型：{model}")
                return (image_bytes, f"OpenRouter/{model.split('/')[-1]}")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[OpenRouter] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(4 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[OpenRouter] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(4 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"OpenRouter 全部重试失败：{last_err}")


def _extract_image(data: dict, log: Callable) -> bytes:
    choices = data.get("choices", [])
    if not choices:
        raise ValueError(f"OpenRouter 响应无 choices：{data}")
    message = choices[0].get("message", {})
    content = message.get("content", "")

    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                img_url_obj = item.get("image_url", {})
                url = img_url_obj.get("url", "") if isinstance(img_url_obj, dict) else img_url_obj
                if url:
                    return _fetch_or_decode(url, log)
                data_b64 = item.get("data", "")
                if data_b64:
                    return base64.b64decode(data_b64)

    if isinstance(content, str) and content.strip():
        return _fetch_or_decode(content.strip(), log)

    raise ValueError(f"OpenRouter 响应中未找到图片，message={message}")


def _fetch_or_decode(url_or_b64: str, log: Callable) -> bytes:
    if url_or_b64.startswith("data:"):
        _, b64_part = url_or_b64.split(",", 1)
        return base64.b64decode(b64_part)
    parsed = urlparse(url_or_b64)
    if parsed.scheme in ("http", "https"):
        log(f"[OpenRouter] 下载图片：{url_or_b64[:80]}…")
        r = requests.get(url_or_b64, timeout=60)
        r.raise_for_status()
        return r.content
    try:
        return base64.b64decode(url_or_b64)
    except Exception:
        raise ValueError(f"无法解析图片来源：{url_or_b64[:80]}")
