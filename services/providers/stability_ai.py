"""
services/providers/stability_ai.py
Stability AI — SD3 嫡系，支持 img2img
端点: POST https://api.stability.ai/v1/generation/stable-diffusion-xl-burn-2/image-to-image
认证: Bearer Token
"""
import base64, io, threading, time
from typing import Callable, Tuple
import requests
from PIL import Image

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 3.0
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_stability_ai(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("stability_key", "").strip()
    if not key:
        raise ValueError("需要 Stability AI API Key！注册：https://platform.stability.ai/")

    engine_id = "stable-diffusion-xl-burn-2"
    headers = {"Authorization": f"Bearer {key}", "Accept": "image/*"}
    form = {"text_prompts[0][text]": prompt,
            "image_structure": "individual"}

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Stability AI] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = requests.post(
                    f"https://api.stability.ai/v1/generation/{engine_id}/text-to-image",
                    headers=headers, data=form, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[Stability AI] 速率限制，等待 30s…"); time.sleep(30); continue
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                _LAST_DONE[0] = time.time()
                log("[Stability AI] 生成成功 ✓")
                return (resp.content, "StabilityAI/SDXL")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Stability AI] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[Stability AI] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Stability AI 全部重试失败：{last_err}")
