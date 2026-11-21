"""
services/providers/minimax_image.py — MiniMax 图像生成（文生图）

支持模型（2026-11-22 换代）：
  · MiniMax-H3-Image           — H3 旗舰（默认；文生图+编辑，最高 20MP）
  · MiniMax-H3-Image-Highspeed — 同参数更快变体

端点: POST https://api.minimax.io/v1/images/generations（OpenAI 风格：
model/prompt/aspect_ratio+area/n/response_format）
认证: Header Authorization: Bearer <key>
响应: data[].url（或 b64_json），usage.generated_images 计成功数

图生图：H3 的编辑走 /v1/images/edits 端点（最多 16 张参考图），
其请求契约尚未核验接入——supports_img2img 暂关，旧 image-01 的
subject_reference 通道随 image-01 退役；edits 接入为后续待办。
"""

import base64
import threading
import time
from typing import Callable, Tuple

import requests

from config.model_catalog import (
    MINIMAX_IMAGE_DEFAULT,
    MINIMAX_IMAGE_MODELS,
    MINIMAX_IMAGE_NAMES,
)
from services.generation.errors import (
    ProviderConfigError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderTransientError,
)
from services.providers._net import (
    get_session as _get_session,
    raise_for_response,
    safe_get_image as _safe_get_image,
)


PROVIDER_INFO = {
    "id": "minimax_image",
    "name": "MiniMax Image (付费)",
    "category": "commercial",
    "config_key": "minimax_key",
    "description": "MiniMax H3-Image 文生图（最高 20MP）",
    "supports_img2img": False,  # H3 编辑端点契约核验后恢复
}


_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 2.0

_ENDPOINT = "https://api.minimax.io/v1/images/generations"
_TIMEOUT = 120
_MAX_RETRIES = 3

# (ratio_value, aspect_ratio 枚举)
_ASPECTS = [
    (1 / 3, "1:3"),
    (3, "3:1"),
    (9 / 16, "9:16"),
    (16 / 9, "16:9"),
    (2 / 3, "2:3"),
    (3 / 2, "3:2"),
    (3 / 4, "3:4"),
    (4 / 3, "4:3"),
    (1, "1:1"),
]


def _best_aspect(w: int, h: int) -> str:
    r = w / max(h, 1)
    return min(_ASPECTS, key=lambda x: abs(x[0] - r))[1]


def _best_area(w: int, h: int) -> str:
    """按请求像素量选 area 档（H3 面积允许 [655360, 20000000] px）。"""
    pixels = max(w, 1) * max(h, 1)
    if pixels <= 1_100_000:
        return "1K"
    if pixels <= 4_500_000:
        return "2K"
    return "4K"


def try_minimax_image(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("minimax_key", "").strip()
    if not key:
        raise ProviderConfigError("需要 MiniMax API Key，请在「💎 付费接口配置」中填写")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    model = cfg.get("minimax_model", "").strip()
    if model not in MINIMAX_IMAGE_MODELS:
        if model:
            log(f"[MiniMax] 模型 {model!r} 不在目录，已归一化到默认 {MINIMAX_IMAGE_DEFAULT}")
        model = MINIMAX_IMAGE_DEFAULT

    aspect = _best_aspect(w, h)
    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect,
        "area": _best_area(w, h),
        "n": 1,
        "response_format": "url",
    }
    log(f"► MiniMax {MINIMAX_IMAGE_NAMES.get(model, model)}  文生图  宽高比={aspect}  档={payload['area']}")

    # ── 持锁范围仅限限速等待：预占时间槽后立即放锁 ──────────────────
    # 修复：原版锁覆盖整个重试循环，429 退避与 HTTP 超时都持锁，
    # 批量并发时其余线程最长被阻塞数分钟。等待/请求均在锁外执行。
    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        _LAST_DONE[0] = time.time()  # 预占时间槽，锁外等待/请求

    last_err = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            log(f"[MiniMax] 尝试 {attempt}/{_MAX_RETRIES}…")
            resp = _get_session().post(
                _ENDPOINT,
                headers=headers,
                json=payload,
                timeout=_TIMEOUT,
            )
            if resp.status_code == 429:
                log("[MiniMax] 速率限制，等待 20s…")
                time.sleep(20)
                continue
            if resp.status_code != 200:
                raise_for_response(resp, "MiniMax Image")

            data = resp.json()
            image_bytes = _extract_image(data)
            log("[MiniMax] 生成成功 ✓")
            return (image_bytes, f"MiniMax/{MINIMAX_IMAGE_NAMES.get(model, model)}")

        except ProviderError:
            raise  # 类型化错误直通：重试/回退由 orchestrator 按 code 决策
        except (ValueError, RuntimeError) as e:
            last_err = e
            log(f"[MiniMax] 错误：{e}")
            if attempt < _MAX_RETRIES:
                time.sleep(3 * attempt)
        except requests.RequestException as e:
            last_err = RuntimeError(str(e))
            log(f"[MiniMax] 网络错误：{e}")
            if attempt < _MAX_RETRIES:
                time.sleep(3 * attempt)

    raise ProviderTransientError(f"MiniMax 全部重试失败：{last_err}")


def _extract_image(data: dict) -> bytes:
    """响应体：{"data": [{"url": ...} | {"error": {...}}], "usage": {...}}。

    HTTP 200 仅代表至少一张成功；单项失败在 error 对象里。
    """
    items = data.get("data", [])
    if not items:
        raise ProviderInvalidResponseError(f"MiniMax 响应中无 data 数组：{data}")
    first = items[0]
    err = first.get("error") if isinstance(first, dict) else None
    if err:
        raise ProviderInvalidResponseError(f"MiniMax 图片生成失败：{err.get('message', err)}")
    url = first.get("url", "")
    b64 = first.get("b64_json", "")
    if b64:
        return base64.b64decode(b64)
    if not url:
        raise ProviderInvalidResponseError(f"MiniMax 响应中既无 url 也无 b64_json：{first}")
    return _safe_get_image(url)
