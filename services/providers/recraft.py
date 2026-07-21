"""
services/providers/recraft.py — Recraft v3 / v4.1
设计/插画/品牌VI首选，OpenAI 兼容接口，支持写实/插画/矢量多风格。
API: POST https://external.api.recraft.ai/v1/images/generations
Key: Header  Authorization: Bearer <key>

风格(recraft_style)可选值：
  realistic_image      — 写实摄影（默认，适合商业图）
  digital_illustration — 数字插画（适合小红书/封面）
  vector_illustration  — 矢量插画（适合品牌/图标）

UPGRADE 2026-07：Recraft 已发布 v4/v4.1（官方 API 默认 model 现为
recraftv4_1），但 v3 仍未弃用，且官方文档说明 inpainting/outpainting
/replace-background 等操作仍要求 v3。由于未能核实 v4.1 下 style 参数
枚举是否与 v3 完全兼容，这里改为可通过 cfg["recraft_model"] 切换
（默认仍是经过验证的 recraftv3），想用更高画质可自行设为 recraftv4_1。
"""
import base64
import threading
import time
import requests
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, validate_image_url as _validate_image_url, safe_error_text as _safe_error_text, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "id": "recraft",
    "name": "Recraft v3 (设计/插画)",
    "category": "commercial",
    "config_key": "recraft_key",
}


_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0

# 支持的输出尺寸（选最接近的）
_SIZES = [
    ((1024, 1024), "1024x1024"),
    ((1365, 1024), "1365x1024"),
    ((1024, 1365), "1024x1365"),
    ((1536, 1024), "1536x1024"),
    ((1024, 1536), "1024x1536"),
    ((1820, 1024), "1820x1024"),
    ((1024, 1820), "1024x1820"),
]


def _best_size(w: int, h: int) -> str:
    r = w / max(h, 1)
    return min(_SIZES, key=lambda x: abs(x[0][0] / x[0][1] - r))[1]


def try_recraft(prompt: str, w: int, h: int, seed: int,
                cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("recraft_key", "").strip()
    if not key:
        raise ValueError("需要 Recraft API Key！注册：https://www.recraft.ai/")

    size  = _best_size(w, h)
    style = cfg.get("recraft_style", "realistic_image")
    model = cfg.get("recraft_model", "recraftv3")
    log(f"► Recraft {model}  尺寸={size}  风格={style}")

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _session.post(
                "https://external.api.recraft.ai/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "prompt": prompt,
                    "style":  style,
                    "n":      1,
                    "size":   size,
                    "model":  model,
                },
                timeout=120,
            )
        except requests.exceptions.ConnectionError as e:
            _LAST_DONE[0] = time.time()
            raise ValueError(f"无法连接 Recraft: {e}")
        _LAST_DONE[0] = time.time()

    log(f"  状态: {resp.status_code}")
    if resp.status_code == 401:
        raise ValueError("Recraft API Key 无效")
    if resp.status_code == 429:
        raise ValueError("Recraft 速率限制")
    if resp.status_code != 200:
        raise ValueError(f"Recraft 返回 {resp.status_code}: {_safe_error_text(resp)}")

    data = resp.json().get("data", [])
    if not data:
        raise ValueError("Recraft 返回数据为空")

    img_url = data[0].get("url", "")
    if img_url:
        data = _safe_get_image(img_url, timeout=60)
        log(f"  ✓ Recraft {model} 成功（URL）{len(data) // 1024}KB")
        return data, f"Recraft/{model}-{style}"

    b64 = data[0].get("b64_json", "")
    if b64:
        img = base64.b64decode(b64)
        log(f"  ✓ Recraft {model} 成功（base64）{len(img) // 1024}KB")
        return img, f"Recraft/{model}-{style}"

    raise ValueError("Recraft 响应中无图片数据")
