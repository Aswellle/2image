"""
services/providers/recraft.py
Recraft V3 — 矢量图/逼真图像，适合 logo、UI 插画
端点: POST https://api.recraft.ai/v3/images/generation
认证: Bearer Token
响应: {data:[{url: "...", revised_prompt: "..."}]}
免费: 50 次/小时
模型: "recraftv3" | "recraftv3FL" | "realistic" | "realisticFL"
"""
import base64, threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0
_ENDPOINT  = "https://api.recraft.ai/v3/images/generation"
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_recraft(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("recraft_key", "").strip()
    if not key:
        raise ValueError("需要 Recraft API Key！注册：https://recraft.ai/（50次/小时免费）")

    model = cfg.get("recraft_model", "recraftv3")
    style = cfg.get("recraft_style", "realistic")
    # Recraft 只支持固定比例
    aspect = "square"       if abs(w-h) < 64 else              "landscape"    if w > h        else              "portrait"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "model": model,
        "style": style,
        "aspect_ratio": aspect,
        "n": 1,
    }
    if seed and seed > 0: payload["seed"] = seed

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Recraft] 尝试 {attempt}/{_MAX_RETRIES}（{model}/{aspect}）…")
                resp = requests.post(_ENDPOINT, headers=headers,
                                     json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[Recraft] 速率限制，等待 30s…"); time.sleep(30); continue
                if resp.status_code == 402:
                    raise ValueError("Recraft 额度用尽，60分钟刷新一次：https://recraft.ai/settings")
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log(f"[Recraft] 生成成功 ✓（{model}/{aspect}）")
                return (image_bytes, f"Recraft/{model}")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Recraft] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(4 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[Recraft] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(4 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Recraft 全部重试失败：{last_err}")

def _extract_image(data, log) -> bytes:
    items = data.get("data", [])
    if not items:
        raise ValueError(f"Recraft 响应无 data：{data}")
    url = items[0].get("url", "")
    if url:
        log(f"[Recraft] 下载图片：{url[:80]}…")
        r = requests.get(url, timeout=60); r.raise_for_status()
        return r.content
    raise ValueError(f"Recraft 响应无 url：{items[0]}")
