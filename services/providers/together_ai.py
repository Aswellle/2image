"""
services/providers/together_ai.py
Together AI — FLUX.1-schnell-Free 免费端点
端点: POST https://api.together.xyz/v1/images/generations
认证: Bearer Token
响应: {data:[{url: "..."}]}
"""
import base64, threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0
_ENDPOINT  = "https://api.together.xyz/v1/images/generations"
_MODEL     = "black-forest-labs/FLUX.1-schnell-Free"
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_together_ai(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("together_key", "").strip()
    if not key:
        raise ValueError("需要 Together AI API Key！注册：https://api.together.ai/")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": _MODEL, "prompt": prompt, "n": 1,
               "width": _clamp(w), "height": _clamp(h)}
    if seed and seed > 0:
        payload["seed"] = seed

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Together AI] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = requests.post(_ENDPOINT, headers=headers,
                                    json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[Together AI] 速率限制，等待 30s…"); time.sleep(30); continue
                if resp.status_code == 402:
                    raise ValueError("Together AI 余额不足，请前往 https://api.together.ai/ 充值。")
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                image_bytes = _extract_image(resp.json(), log)
                _LAST_DONE[0] = time.time()
                log("[Together AI] 生成成功 ✓")
                return (image_bytes, "TogetherAI/FLUX.1-schnell-Free")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Together AI] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[Together AI] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Together AI 全部重试失败：{last_err}")

def _extract_image(data, log) -> bytes:
    items = data.get("data", [])
    if not items:
        raise ValueError(f"Together AI 响应无 data 字段：{data}")
    url = items[0].get("url", "")
    if url:
        log(f"[Together AI] 下载图片：{url[:80]}…")
        r = requests.get(url, timeout=60); r.raise_for_status()
        return r.content
    b64 = items[0].get("b64_json", "")
    if b64:
        return base64.b64decode(b64)
    raise ValueError(f"Together AI 响应无 url 或 b64_json：{items[0]}")

def _clamp(px: int) -> int:
    px = max(256, min(1440, px))
    return round(px / 64) * 64
