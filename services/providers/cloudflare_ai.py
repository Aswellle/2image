"""
services/providers/cloudflare_ai.py
Cloudflare Workers AI — 免费 10,000 次/天，全球 CDN
端点: POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run
认证: Bearer Token (API Token)
响应: 图片二进制流
"""
import threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 1.0
_MODEL     = "@cf/stable-diffusion-xl-base-1.0"
_TIMEOUT  = 90
_MAX_RETRIES = 3

def try_cloudflare_ai(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    account_id = cfg.get("cf_account_id", "").strip()
    api_token  = cfg.get("cf_api_token", "").strip()
    if not account_id or not api_token:
        raise ValueError("需要 Cloudflare Account ID + API Token！"
                         "注册：https://dash.cloudflare.com/")

    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    payload = {
        "prompt": prompt,
        "num_steps": 20,
        "width": min(max(w, 512), 1024),
        "height": min(max(h, 512), 1024),
    }
    if seed and seed > 0: payload["seed"] = seed
    endpoint = (f"https://api.cloudflare.com/client/v4/accounts/"
                f"{account_id}/ai/run/{_MODEL}")

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Cloudflare AI] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = requests.post(endpoint, headers=headers,
                                     json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[Cloudflare AI] 速率限制，等待 15s…"); time.sleep(15); continue
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                _LAST_DONE[0] = time.time()
                log("[Cloudflare AI] 生成成功 ✓")
                return (resp.content, "CloudflareAI/SDXL")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Cloudflare AI] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[Cloudflare AI] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Cloudflare AI 全部重试失败：{last_err}")
