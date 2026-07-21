"""
services/providers/openrouter.py
OpenRouter 统一 Image API
端点: POST https://openrouter.ai/api/v1/images
认证: Bearer Token
响应: data[].b64_json

FIX 2026-07: OpenRouter 已上线专门的统一 Image API（/api/v1/images），
官方博客称之后"新图像模型只会加到这个专用 Image API"，旧的
/api/v1/chat/completions + modalities:["image"] 路由是否还继续可用
未被确认，故直接切到新端点。另外：截至目前没有在官方文档/博客里找到
任何 $0 价格的免费图像模型（旧默认的 "FLUX.1-schnell:free" 这类
":free" 图像模型后缀未再出现），免费可用性存疑——保留 free 分类是
延续现有归类，实际以账户余量为准，失败时会被调度器跳过。
"""

import threading
import time
import base64
import requests
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text


PROVIDER_INFO = {
    "id": "openrouter",
    "name": "OpenRouter (统一 Image API)",
    "category": "free",
    "config_key": "openrouter_key",
}


# ── 串行锁 ────────────────────────────────────────────────────────────
_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 3.0

_ENDPOINT = "https://openrouter.ai/api/v1/images"
# 官方文档 image-generation 指南里给出的示例模型 slug（已确认可用，
# 非免费）；具体可用/免费模型请到 openrouter.ai/models?modality=image
# 核实后在「付费接口配置」里的「图像模型」栏自行替换。
_DEFAULT_MODEL = "bytedance-seed/seedream-4.5"
_TIMEOUT = 120
_MAX_RETRIES = 3


def try_openrouter(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("openrouter_key", "").strip()
    if not key:
        raise ValueError(
            "需要 OpenRouter API Key！注册：https://openrouter.ai/keys"
        )

    model = cfg.get("openrouter_model", "").strip() or _DEFAULT_MODEL

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": f"{w}x{h}",
    }
    if seed and seed > 0:
        payload["seed"] = seed

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[OpenRouter] 尝试 {attempt}/{_MAX_RETRIES}，模型：{model}…")
                resp = _session.post(
                    _ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=_TIMEOUT,
                )
                if resp.status_code == 429:
                    log("[OpenRouter] 速率限制，等待 30s…")
                    time.sleep(30)
                    continue
                if resp.status_code == 402:
                    raise ValueError("OpenRouter 余额不足，请充值或更换其他模型。")
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {_safe_error_text(resp)}"
                    )

                data = resp.json()
                image_bytes = _extract_image(data)
                _LAST_DONE[0] = time.time()
                log(f"[OpenRouter] 生成成功 ✓ 模型：{model}")
                return (image_bytes, f"OpenRouter/{model.split('/')[-1]}")

            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[OpenRouter] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(4 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                log(f"[OpenRouter] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(4 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"OpenRouter 全部重试失败：{last_err}")


def _extract_image(data: dict) -> bytes:
    """统一 Image API 响应：data[].b64_json。"""
    items = data.get("data", [])
    if not items:
        raise ValueError(f"OpenRouter 响应无 data 字段：{data}")

    b64 = items[0].get("b64_json", "")
    if not b64:
        raise ValueError(f"OpenRouter 响应中未找到 b64_json：{items[0]}")
    return base64.b64decode(b64)
