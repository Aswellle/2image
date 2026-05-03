"""
services/providers/siliconflow.py
硅基流动 — FLUX.1-pro 等，低价稳定，国内可访问
端点: POST https://api.siliconflow.cn/v1/images/generations
认证: Bearer Token
响应: {data:[{url: "..."}]}
"""
import base64, threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0
_ENDPOINT  = "https://api.siliconflow.cn/v1/images/generations"
_MODEL     = "stabilityai/stable-diffusion-3-medium"
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_siliconflow(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("siliconflow_key", "").strip()
    if not key:
        raise ValueError("需要硅基流动 API Key！注册：https://cloud.siliconflow.cn/")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": _MODEL, "prompt": prompt, "n": 1,
               "width": w, "height": h}
    if seed and seed > 0: payload["seed"] = seed

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[SiliconFlow] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = requests.post(_ENDPOINT, headers=headers,
                                    json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[SiliconFlow] 速率限制，等待 30s…"); time.sleep(30); continue
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                image_bytes = _extract_image(resp.json(), log)
                _LAST_DONE[0] = time.time()
                log("[SiliconFlow] 生成成功 ✓")
                return (image_bytes, "SiliconFlow/SD3-Medium")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[SiliconFlow] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[SiliconFlow] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"SiliconFlow 全部重试失败：{last_err}")

def _extract_image(data, log) -> bytes:
    items = data.get("data", [])
    if not items:
        raise ValueError(f"SiliconFlow 响应无 data：{data}")
    url = items[0].get("url", "")
    if url:
        log(f"[SiliconFlow] 下载图片：{url[:80]}…")
        r = requests.get(url, timeout=60); r.raise_for_status()
        return r.content
    b64 = items[0].get("b64_json", "")
    if b64:
        return base64.b64decode(b64)
    raise ValueError(f"SiliconFlow 响应无 url 或 b64_json")
