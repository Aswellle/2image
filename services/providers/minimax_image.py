"""
services/providers/minimax_image.py — MiniMax 图像生成（文生图 + 图生图）

支持模型：
  · image-01 — MiniMax 图像生成模型（当前唯一可用）

端点: POST https://api.minimax.io/v1/image_generation
认证: Header Authorization: Bearer <key>
响应: data.image_base64[]  (base64 数组)

图生图使用 subject_reference（主体参考图）模式。
"""
import base64
import threading
import time
from typing import Callable, Tuple

import requests

from config.model_catalog import MINIMAX_IMAGE_DEFAULT, MINIMAX_IMAGE_NAMES
from services.providers._net import get_session as _get_session, safe_error_text as _safe_error_text


PROVIDER_INFO = {
    "id": "minimax_image",
    "name": "MiniMax Image 01 (免费试用)",
    "category": "commercial",
    "config_key": "minimax_key",
    "description": "MiniMax image-01 文生图/图生图",
}








_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0

_MODEL = MINIMAX_IMAGE_DEFAULT
_ENDPOINT = "https://api.minimax.io/v1/image_generation"
_TIMEOUT  = 120
_MAX_RETRIES = 3

# (ratio_value, aspect_ratio 枚举)
_ASPECTS = [
    (1/3, "1:3"), (3, "3:1"),
    (9/16, "9:16"), (16/9, "16:9"),
    (2/3, "2:3"), (3/2, "3:2"),
    (3/4, "3:4"), (4/3, "4:3"),
    (1, "1:1"),
]


def _best_aspect(w: int, h: int) -> str:
    r = w / max(h, 1)
    return min(_ASPECTS, key=lambda x: abs(x[0] - r))[1]


def _guess_mime(image_bytes: bytes) -> str:
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def try_minimax_image(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("minimax_key", "").strip()
    if not key:
        raise ValueError("需要 MiniMax API Key，请在「💎 付费接口配置」中填写")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }

    aspect = _best_aspect(w, h)
    payload = {
        "model":           _MODEL,
        "prompt":          prompt,
        "aspect_ratio":    aspect,
        "response_format": "base64",
    }

    ref_image = cfg.get("_ref_image")   # bytes or None（图生图参考图）
    if ref_image is not None:
        mime = _guess_mime(ref_image)
        data_uri = f"data:{mime};base64,{base64.b64encode(ref_image).decode('ascii')}"
        payload["subject_reference"] = [{"type": "character", "image_file": data_uri}]
        log(f"► MiniMax image-01  图生图（主体参考图）  宽高比={aspect}")
    else:
        log(f"► MiniMax image-01  文生图  宽高比={aspect}")

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
                _ENDPOINT, headers=headers, json=payload, timeout=_TIMEOUT,
            )
            if resp.status_code == 429:
                log("[MiniMax] 速率限制，等待 20s…")
                time.sleep(20)
                continue
            if resp.status_code != 200:
                raise RuntimeError(
                    f"HTTP {resp.status_code}: {_safe_error_text(resp)}"
                )

            data = resp.json()
            image_bytes = _extract_image(data)
            log("[MiniMax] 生成成功 ✓")
            return (image_bytes, f"MiniMax/{MINIMAX_IMAGE_NAMES.get(_MODEL, _MODEL)}")

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

    raise RuntimeError(f"MiniMax 全部重试失败：{last_err}")

def _extract_image(data: dict) -> bytes:
    """响应体：{"data": {"image_base64": ["<b64>", ...]}, "base_resp": {...}}。"""
    base_resp = data.get("base_resp", {})
    if base_resp.get("status_code", 0) not in (0, None):
        raise ValueError(f"MiniMax 错误：{base_resp.get('status_msg', data)}")

    images = data.get("data", {}).get("image_base64", [])
    if not images:
        raise ValueError(f"MiniMax 响应中无 image_base64：{data}")
    return base64.b64decode(images[0])
