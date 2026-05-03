"""
services/providers/openai_dalle.py
OpenAI DALL-E 3 — 行业标杆
端点: POST https://api.openai.com/v1/images/generations
认证: Bearer Token
响应: {data:[{url: "..."}]}
"""
import base64, threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 3.0
_ENDPOINT  = "https://api.openai.com/v1/images/generations"
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_openai_dalle(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("openai_key", "").strip()
    if not key:
        raise ValueError("需要 OpenAI API Key！获取：https://platform.openai.com/api-keys")

    model = cfg.get("dalle_model", "dall-e-3")
    quality = cfg.get("dalle_quality", "standard")
    size = f"{min(w, 1792)}x{min(h, 1792)}"

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": model, "prompt": prompt, "n": 1,
               "size": size, "quality": quality}

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[DALL-E] 尝试 {attempt}/{_MAX_RETRIES}（{model}）…")
                resp = requests.post(_ENDPOINT, headers=headers,
                                     json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[DALL-E] 速率限制，等待 30s…"); time.sleep(30); continue
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                image_bytes = _extract_image(resp.json(), log)
                _LAST_DONE[0] = time.time()
                log(f"[DALL-E] 生成成功 ✓（{model}）")
                return (image_bytes, f"DALL-E/{model}")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[DALL-E] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[DALL-E] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"DALL-E 全部重试失败：{last_err}")

def _extract_image(data, log) -> bytes:
    items = data.get("data", [])
    if not items:
        raise ValueError(f"DALL-E 响应无 data：{data}")
    url = items[0].get("url", "")
    if url:
        log(f"[DALL-E] 下载图片：{url[:80]}…")
        r = requests.get(url, timeout=60); r.raise_for_status()
        return r.content
    b64 = items[0].get("b64_json", "")
    if b64:
        return base64.b64decode(b64)
    raise ValueError("DALL-E 响应无 url 或 b64_json")
