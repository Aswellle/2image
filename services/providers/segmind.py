"""
services/providers/segmind.py
Segmind — 注册送 $5，支持 img2img
端点: POST https://api.segmind.com/v1/enterprise/invoke/sdxl
认证: Bearer Token
"""
import base64, threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0
_ENDPOINT  = "https://api.segmind.com/v1/enterprise/invoke/sdxl"
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_segmind(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("segmind_key", "").strip()
    if not key:
        raise ValueError("需要 Segmind API Key！注册：https://segmind.com/（注册送 $5）")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, watermark",
        "samples": 1,
        "width": min(max(w, 512), 1536),
        "height": min(max(h, 512), 1536),
        "steps": 30,
        "scale": 7.5,
        "seed": seed if seed and seed > 0 else None,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Segmind] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = requests.post(_ENDPOINT, headers=headers,
                                     json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[Segmind] 速率限制，等待 30s…"); time.sleep(30); continue
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log("[Segmind] 生成成功 ✓")
                return (image_bytes, "Segmind/SDXL")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Segmind] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[Segmind] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Segmind 全部重试失败：{last_err}")

def _extract_image(data, log) -> bytes:
    # Segmind 返回 {images: [{image: "base64..."}]}
    images = data.get("images", [])
    if images:
        b64 = images[0].get("image", "")
        if b64:
            return base64.b64decode(b64)
    # 也可能是 data: [...]
    items = data.get("data", [])
    if items:
        b64 = items[0].get("image", "") or items[0].get("base64", "")
        if b64:
            return base64.b64decode(b64)
    raise ValueError(f"Segmind 响应格式未知：{list(data.keys())}")
