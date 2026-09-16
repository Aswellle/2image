"""
services/providers/volcengine_ark.py — 火山引擎豆包生图（文生图 + 图生图）

支持模型：
  · doubao-seedream-3-0-t2i  — 豆包文生图 3.0
  · doubao-seedream-4-0-t2i  — 豆包文生图 4.0（最新最强）
  · doubao-seededit-3-0-i2i  — 豆包图生图 3.0

端点：POST https://ark.cn-beijing.volces.com/api/v3/images/generations
认证：Header Authorization: Bearer <key>
响应：data[].url 或 data[].b64_json

参考：火山引擎 Ark SDK (volcengine-python-sdk)
"""
import base64
import threading
import time
from typing import Callable, Tuple

from config.model_catalog import (
    ARK_IMAGE_DEFAULT,
    ARK_IMAGE_NAMES,
)
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text


PROVIDER_INFO = {
    "id": "volcengine_ark",
    "name": "豆包 Seedream (火山引擎)",
    "category": "commercial",
    "config_key": "volcengine_key",
    "description": "豆包 Seedream 3.0/4.0 文生图，SeedEdit 3.0 图生图",
}

# ── 串行锁（防批量并发触发速率限制）──────────────────────────────
_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 1.5

_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
_TIMEOUT = 120
_MAX_RETRIES = 3

# 支持的尺寸
_SUPPORTED_SIZES = [
    "1024x1024", "1280x720", "720x1280",
    "1440x960", "960x1440", "2048x2048",
]


def _best_size(w: int, h: int) -> str:
    """取最接近的支持尺寸"""
    def score(s):
        sw, sh = map(int, s.split("x"))
        return abs(sw - w) + abs(sh - h)
    return min(_SUPPORTED_SIZES, key=score)


def try_volcengine_ark(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("volcengine_key", "").strip()
    if not key:
        raise ValueError("需要火山引擎 API Key，请在配置中填写")

    # 模型选择：图生图自动使用 SeedEdit，文生图使用配置的模型
    ref_image = cfg.get("_ref_image")
    if ref_image is not None:
        model = "doubao-seededit-3-0-i2i"
    else:
        model = cfg.get("ark_model", ARK_IMAGE_DEFAULT)

    size_str = _best_size(w, h)
    display_name = ARK_IMAGE_NAMES.get(model, model)

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size_str,
        "response_format": "url",
        "seed": seed if seed else None,
        "guidance_scale": 2.5,
        "watermark": False,
    }

    # 图生图：传入参考图
    if ref_image is not None:
        mime = "image/png"
        if ref_image[:8] == b"\x89PNG\r\n\x1a\n":
            mime = "image/png"
        elif ref_image[:3] == b"\xff\xd8\xff":
            mime = "image/jpeg"
        b64 = base64.b64encode(ref_image).decode("ascii")
        payload["image"] = f"data:{mime};base64,{b64}"
        log(f"► 豆包 {display_name}  图生图  尺寸={size_str}")
    else:
        log(f"► 豆包 {display_name}  文生图  尺寸={size_str}")

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[豆包] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = _session.post(
                    _ENDPOINT, headers=headers, json=payload, timeout=_TIMEOUT,
                )
                if resp.status_code == 429:
                    log("[豆包] 速率限制，等待 15s…")
                    time.sleep(15)
                    continue
                if resp.status_code == 401:
                    raise ValueError("火山引擎 API Key 无效或已过期")
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {_safe_error_text(resp)}"
                    )

                data = resp.json()
                items = data.get("data", [])
                if not items:
                    raise ValueError("豆包返回数据中无图片")

                # 优先使用 b64_json，否则下载 URL
                b64 = items[0].get("b64_json", "")
                if b64:
                    image_bytes = base64.b64decode(b64)
                else:
                    img_url = items[0].get("url", "")
                    if not img_url:
                        raise ValueError("豆包返回数据中无图片 URL")
                    img_resp = _session.get(img_url, timeout=60)
                    img_resp.raise_for_status()
                    image_bytes = img_resp.content

                _LAST_DONE[0] = time.time()
                log("[豆包] 生成成功 ✓")
                return (image_bytes, f"豆包/{display_name}")

            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[豆包] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)
            except Exception as e:
                last_err = RuntimeError(str(e))
                log(f"[豆包] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"豆包全部重试失败：{last_err}")
