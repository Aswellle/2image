"""
services/providers/xai_grok.py
xAI Grok Imagine — Aurora 模型，注册送 $25，$0.07/张
端点: POST https://api.x.ai/v1/images/generations
认证: Bearer Token
模型: grok-2-image-1212（固定 1024x1024）
"""
import base64, threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0
_ENDPOINT  = "https://api.x.ai/v1/images/generations"
_MODEL     = "grok-2-image-1212"
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_xai_grok(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("xai_key", "").strip()
    if not key:
        raise ValueError("需要 xAI API Key！注册：https://x.ai/api（注册送 $25）")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": _MODEL, "prompt": prompt, "n": 1,
               "response_format": "url"}

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[xAI Grok] 尝试 {attempt}/{_MAX_RETRIES}（Aurora，固定 1024x1024）…")
                resp = requests.post(_ENDPOINT, headers=headers,
                                      json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[xAI Grok] 速率限制，等待 30s…"); time.sleep(30); continue
                if resp.status_code == 402:
                    raise ValueError("xAI 余额不足！充值：https://console.x.ai（消费满 $5 可获 $150/月额外额度）")
                if resp.status_code == 401:
                    raise ValueError("xAI API Key 无效，请前往 https://console.x.ai 重新生成。")
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                image_bytes = _extract_image(resp.json(), log)
                _LAST_DONE[0] = time.time()
                log("[xAI Grok] 生成成功 ✓ (Aurora / 1024x1024 JPEG)")
                return (image_bytes, f"xAI/{_MODEL}")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[xAI Grok] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(4 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[xAI Grok] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(4 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"xAI Grok 全部重试失败：{last_err}")

def _extract_image(data, log) -> bytes:
    items = data.get("data", [])
    if not items:
        raise ValueError(f"xAI 响应无 data：{data}")
    url = items[0].get("url", "")
    if url:
        log(f"[xAI Grok] 下载图片：{url[:80]}…")
        r = requests.get(url, timeout=60); r.raise_for_status()
        return r.content
    b64 = items[0].get("b64_json", "")
    if b64:
        return base64.b64decode(b64)
    raise ValueError(f"xAI 响应无 url 或 b64_json")
