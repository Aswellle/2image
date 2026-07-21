"""
services/providers/bria_ai.py — Bria AI Fibo 文生图（商业安全/IP 合规定位）
端点: POST https://engine.prod.bria-api.com/v2/image/generate
认证: Header api_token: <key>
请求 sync=true 走同步返回，避免额外实现轮询：
  响应: {"result": {"image_url": ..., "seed": ..., "structured_prompt": ...},
         "request_id": ...}
新用户注册送 1000 次免费调用。
"""
import threading
import time
import requests
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "id": "bria_ai",
    "name": "Bria AI Fibo (免费1000次)",
    "category": "free",
    "config_key": "bria_key",
}


_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 1.5

_ENDPOINT = "https://engine.prod.bria-api.com/v2/image/generate"
_TIMEOUT  = 90

# 官方枚举（OpenAPI 规格确认）
_ASPECTS = [
    (1, "1:1"), (2/3, "2:3"), (3/2, "3:2"), (3/4, "3:4"), (4/3, "4:3"),
    (4/5, "4:5"), (5/4, "5:4"), (9/16, "9:16"), (16/9, "16:9"),
]


def _best_aspect(w: int, h: int) -> str:
    r = w / max(h, 1)
    return min(_ASPECTS, key=lambda x: abs(x[0] - r))[1]


def try_bria_ai(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("bria_key", "").strip()
    if not key:
        raise ValueError("需要 Bria AI API Key，注册送 1000 次免费调用：https://platform.bria.ai/")

    headers = {"api_token": key, "Content-Type": "application/json"}
    payload = {
        "prompt":       prompt,
        "sync":         True,   # 同步返回，避免额外轮询
        "aspect_ratio": _best_aspect(w, h),
        "seed":         seed % 2_147_483_647,
    }
    log(f"► Bria AI Fibo  宽高比={payload['aspect_ratio']}")

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _session.post(_ENDPOINT, headers=headers,
                                 json=payload, timeout=_TIMEOUT)
        except requests.exceptions.ConnectionError as e:
            _LAST_DONE[0] = time.time()
            raise ValueError(f"无法连接 Bria AI: {e}")
        _LAST_DONE[0] = time.time()

    log(f"  状态: {resp.status_code}")
    if resp.status_code == 401:
        raise ValueError("Bria AI API Key 无效")
    if resp.status_code == 402:
        raise ValueError("Bria AI 免费额度已用完，请前往 https://platform.bria.ai/ 查看余量")
    if resp.status_code == 429:
        raise ValueError("Bria AI 速率限制，请稍后再试")
    if resp.status_code != 200:
        raise ValueError(f"Bria AI 返回 {resp.status_code}: {_safe_error_text(resp)}")

    j = resp.json()
    img_url = j.get("result", {}).get("image_url", "")
    if not img_url:
        raise ValueError(f"Bria AI 响应中无 image_url：{j}")

    log("  下载图片中…")
    data = _safe_get_image(img_url, timeout=60)
    log(f"  ✓ Bria AI 成功  {len(data)//1024}KB")
    return data, "BriaAI/Fibo"
