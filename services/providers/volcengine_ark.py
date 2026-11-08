"""
services/providers/volcengine_ark.py — 火山引擎豆包生图（文生图 + 图生图）

支持模型（正式 ID 为带日期快照，方舟文档示例同款）：
  · doubao-seedream-4-5-251128  — Seedream 4.5（综合最佳，默认）
  · doubao-seedream-4-0-250828  — Seedream 4.0（原生支持参考图编辑）
  · doubao-seedream-3-0-t2i     — Seedream 3.0（旧版）
  · doubao-seededit-3-0-i2i     — SeedEdit 3.0（旧版图生图通道）

注意："-t2i" 后缀 ID 仅 3.0 时代有效，4.0 起官方模型表只收录带日期
快照 ID，传 -t2i 后缀会报「模型不存在」。

端点：POST https://ark.cn-beijing.volces.com/api/v3/images/generations
认证：Header Authorization: Bearer <key>
响应：data[].url 或 data[].b64_json

参考：火山引擎 Ark SDK (volcengine-python-sdk)
"""

import base64
import threading
import time
from typing import Callable, Tuple

import requests

from config.model_catalog import (
    ARK_IMAGE_DEFAULT,
    ARK_IMAGE_MODELS,
    ARK_IMAGE_NAMES,
    ARK_NATIVE_I2I_MODELS,
    ARK_SEEDIT_30_I2I,
)
from services.generation.errors import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderTransientError,
)
from services.providers._net import (
    get_session as _get_session,
    safe_error_text as _safe_error_text,
    safe_get_image as _safe_get_image,
    raise_for_response,
)


PROVIDER_INFO = {
    "id": "volcengine_ark",
    "name": "豆包 Seedream (火山引擎)",
    "category": "commercial",
    "config_key": "volcengine_key",
    "description": "豆包 Seedream 4.5/4.0 文生图与原生图生图，SeedEdit 3.0 兜底",
    "supports_img2img": True,
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
    "1024x1024",
    "1280x720",
    "720x1280",
    "1440x960",
    "960x1440",
    "2048x2048",
]


def _best_size(w: int, h: int) -> str:
    """取最接近的支持尺寸"""

    def score(s):
        sw, sh = map(int, s.split("x"))
        return abs(sw - w) + abs(sh - h)

    return min(_SUPPORTED_SIZES, key=score)


def try_volcengine_ark(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("volcengine_key", "").strip()
    if not key:
        raise ProviderConfigError("需要火山引擎 API Key，请在配置中填写")

    # 模型选择：文生图用配置模型；图生图优先用 Seedream 4.x 原生
    # 参考图编辑（官方教程推荐，保持主体一致性优于旧 SeedEdit 3.0），
    # 配置模型不支持原生编辑（如 3.0/SeedEdit）时回退 SeedEdit 3.0。
    ref_image = cfg.get("_ref_image")
    model = cfg.get("ark_model", "").strip()
    if model not in ARK_IMAGE_MODELS:
        # 存量无效值（如旧的 -t2i 后缀 ID）与空值都归一化；下拉为只读，
        # 目录外值只会来自旧版本配置
        if model:
            log(f"[豆包] 模型 {model!r} 不在目录，已归一化到默认 {ARK_IMAGE_DEFAULT}")
        model = ARK_IMAGE_DEFAULT
    if ref_image is not None and model not in ARK_NATIVE_I2I_MODELS:
        model = ARK_SEEDIT_30_I2I

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
            log(f"[豆包] 尝试 {attempt}/{_MAX_RETRIES}…")
            resp = _get_session().post(
                _ENDPOINT,
                headers=headers,
                json=payload,
                timeout=_TIMEOUT,
            )
            if resp.status_code == 429:
                log("[豆包] 速率限制，等待 15s…")
                time.sleep(15)
                continue
            if resp.status_code == 401:
                raise ProviderAuthError("火山引擎 API Key 无效或已过期")
            if resp.status_code != 200:
                raise_for_response(resp, "豆包 Seedream (火山引擎)")

            data = resp.json()
            items = data.get("data", [])
            if not items:
                raise ProviderInvalidResponseError("豆包返回数据中无图片")

            # 优先使用 b64_json，否则下载 URL
            b64 = items[0].get("b64_json", "")
            if b64:
                image_bytes = base64.b64decode(b64)
            else:
                img_url = items[0].get("url", "")
                if not img_url:
                    raise ProviderInvalidResponseError("豆包返回数据中无图片 URL")
                image_bytes = _safe_get_image(img_url)

            log("[豆包] 生成成功 ✓")
            return (image_bytes, f"豆包/{display_name}")

        except ProviderError:
            raise  # 类型化错误直通：重试/回退由 orchestrator 按 code 决策
        except (ValueError, RuntimeError) as e:
            last_err = e
            log(f"[豆包] 错误：{e}")
            if attempt < _MAX_RETRIES:
                time.sleep(3 * attempt)
        except requests.RequestException as e:
            last_err = RuntimeError(str(e))
            log(f"[豆包] 网络错误：{e}")
            if attempt < _MAX_RETRIES:
                time.sleep(3 * attempt)

    if last_err is None:  # 全部尝试都被内联 429 消耗时没有任何错误记录
        last_err = RuntimeError("全部尝试均触发速率限制（429）")
    raise ProviderTransientError(f"豆包全部重试失败：{last_err}")
