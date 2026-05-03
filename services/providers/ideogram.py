"""
services/providers/ideogram.py
Ideogram — 文字生成图像天花板，真实照片级质量
端点: POST https://api.ideogram.ai/v2/images/generate
认证: Bearer Token
响应: {data:[{url: "...", seed: N}]}
免费: 注册送 100 credits，$5/月起
"""
import base64, threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0
_ENDPOINT  = "https://api.ideogram.ai/v2/images/generate"
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_ideogram(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("ideogram_key", "").strip()
    if not key:
        raise ValueError("需要 Ideogram API Key！注册：https://ideogram.ai/api")

    style = cfg.get("ideogram_style", "REALISTIC")
    # IDEOGRAM ONLY supports specific sizes: 1024x1024, 1792x1024, 1024x1792, 768x768
    if w >= 1024 and h >= 1024:
        size = "1792x1024" if w > h else "1024x1792"
    elif w >= 768 and h >= 768:
        size = "1024x1024"
    else:
        size = "768x768"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "image_request": {
            "prompt": prompt,
            "aspect_ratio": size,
            "style": style,
            "magic_prompt_option": "AUTO",
        }
    }
    if seed and seed > 0:
        payload["image_request"]["seed"] = seed

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Ideogram] 尝试 {attempt}/{_MAX_RETRIES}（{size} / {style}）…")
                resp = requests.post(_ENDPOINT, headers=headers,
                                     json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[Ideogram] 速率限制，等待 30s…"); time.sleep(30); continue
                if resp.status_code == 402:
                    raise ValueError("Ideogram 余额不足，请充值：https://ideogram.ai/settings/billing")
                if resp.status_code == 401:
                    raise ValueError("Ideogram API Key 无效，请前往 https://ideogram.ai/api 重新生成。")
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log(f"[Ideogram] 生成成功 ✓（{size}）")
                return (image_bytes, f"Ideogram/{size}")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Ideogram] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(4 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[Ideogram] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(4 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Ideogram 全部重试失败：{last_err}")

def _extract_image(data, log) -> bytes:
    items = data.get("data", [])
    if not items:
        raise ValueError(f"Ideogram 响应无 data：{data}")
    url = items[0].get("url", "")
    if url:
        log(f"[Ideogram] 下载图片：{url[:80]}…")
        r = requests.get(url, timeout=60); r.raise_for_status()
        return r.content
    raise ValueError(f"Ideogram 响应无 url：{items[0]}")
