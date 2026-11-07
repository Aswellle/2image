"""
services/providers/fal_flux.py — fal.ai FLUX.2 [pro]（文生图 + 图生图）
· 文生图: fal-ai/flux-2-pro（官方旗舰，image_size 任意宽高，最高 4MP）
· 图生图: fal-ai/flux-2-pro/edit（prompt + image_urls 指令式编辑，
  最多 8 张参考图；FLUX.2 单模型同时承担生成与编辑）
API 均为队列提交 + 轮询模式（queue.fal.run）
Key: Header  Authorization: Key <key>

2026-11 更新：对照 fal.ai 官方 openapi schema 核实——
flux-2-pro 输入为 prompt/image_size{width,height}/seed/output_format/
safety_tolerance/sync_mode；edit 端点必填 prompt+image_urls，
image_size 缺省 auto（跟随参考图）。旧端点 flux-pro/v1.1-ultra 与
flux-general/image-to-image 虽仍在线但已非官方主推。
"""

import base64
import threading
import time
from typing import Callable, Tuple
from services.generation.errors import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTransientError,
    classify_http_error,
)
from services.providers._net import (
    get_session as _get_session,
    safe_error_text as _safe_error_text,
    safe_get_image as _safe_get_image,
    raise_if_cancelled as _raise_if_cancelled,
)

PROVIDER_INFO = {
    "id": "fal_flux",
    "name": "fal.ai FLUX.2 Pro (高质量)",
    "category": "commercial",
    "config_key": "fal_key",
    "supports_img2img": True,
}


_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 3.0  # 提交间隔
_POLL_SEC = 3.0  # 轮询间隔
_MAX_POLLS = 40  # 最多等 120s

_QUEUE_T2I = "https://queue.fal.run/fal-ai/flux-2-pro"
_QUEUE_I2I = "https://queue.fal.run/fal-ai/flux-2-pro/edit"


def _clamp_dims(w: int, h: int) -> dict:
    """钳制到合理输出范围（256–2048、16 的倍数），供 image_size 使用。"""
    cw = max(256, min(2048, round(w / 16) * 16))
    ch = max(256, min(2048, round(h / 16) * 16))
    return {"width": cw, "height": ch}


def _poll_fal(request_id: str, queue_base: str, headers: dict, cfg: dict, log: Callable) -> bytes:
    """轮询 fal.ai 队列直到完成，返回图片字节。"""
    status_url = f"{queue_base}/requests/{request_id}"
    result_url = f"{queue_base}/requests/{request_id}/response"
    for i in range(_MAX_POLLS):
        _raise_if_cancelled(cfg)
        time.sleep(_POLL_SEC)
        try:
            st = _get_session().get(status_url, headers=headers, timeout=15)
        except Exception as e:
            log(f"  轮询错误: {e}")
            continue
        if st.status_code != 200:
            continue
        status = st.json().get("status", "")
        log(f"  [{i + 1}] {status}")
        if status == "COMPLETED":
            res = _get_session().get(result_url, headers=headers, timeout=20)
            if res.status_code != 200:
                raise classify_http_error(res.status_code, f"fal.ai 结果获取失败: {res.status_code}")
            images = res.json().get("images", [])
            if not images:
                raise ProviderInvalidResponseError("fal.ai 结果中无图片")
            img_url = images[0].get("url", "")
            if not img_url:
                raise ProviderInvalidResponseError("fal.ai 结果中无图片 URL")
            log("  下载图片中…")
            return _safe_get_image(img_url, timeout=120)
        if status in ("FAILED", "CANCELLED"):
            raise ProviderInvalidResponseError(f"fal.ai 任务失败: {status}")
    raise ProviderTransientError("fal.ai 等待超时（>120s），建议检查网络或换用其他接口")


def try_fal_flux(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("fal_key", "").strip()
    if not key:
        raise ProviderConfigError("需要 fal.ai API Key！注册：https://fal.ai/")

    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    ref_image = cfg.get("_ref_image")  # bytes or None

    if ref_image is not None:
        # ── 图生图模式：flux-2-pro/edit（指令式编辑，image_urls 列表）──
        b64 = base64.b64encode(ref_image).decode()
        log("► fal.ai FLUX.2 Pro  图生图（指令式编辑）")
        payload = {
            "prompt": prompt,
            "image_urls": [f"data:image/png;base64,{b64}"],
            "seed": seed % 2_147_483_647,
            "output_format": "png",
        }
        queue_base = _QUEUE_I2I
        label = "fal.ai/FLUX.2-Pro-edit"
    else:
        # ── 文生图模式：flux-2-pro，image_size 任意宽高 ──────────────
        size = _clamp_dims(w, h)
        log(f"► fal.ai FLUX.2 Pro  文生图  {size['width']}×{size['height']}")
        payload = {
            "prompt": prompt,
            "image_size": size,
            "seed": seed % 2_147_483_647,
            "output_format": "png",
        }
        queue_base = _QUEUE_T2I
        label = "fal.ai/FLUX.2-Pro"

    # ── 提交到队列（持锁以控制提交频率）──────────────────────────
    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _get_session().post(queue_base, headers=headers, json=payload, timeout=30)
        except Exception as e:
            _LAST_DONE[0] = time.time()
            raise ProviderTransientError(f"无法连接 fal.ai: {e}")
        _LAST_DONE[0] = time.time()

    if resp.status_code == 401:
        raise ProviderAuthError("fal.ai API Key 无效")
    if resp.status_code == 429:
        raise ProviderRateLimitError("fal.ai 速率限制，请稍后再试")
    if resp.status_code != 200:
        raise classify_http_error(resp.status_code, f"fal.ai 返回 {resp.status_code}: {_safe_error_text(resp)}")

    request_id = resp.json().get("request_id", "")
    if not request_id:
        raise ProviderInvalidResponseError("fal.ai 未返回 request_id")
    log(f"  已提交  ID={request_id[:14]}…  等待生成…")

    # ── 轮询（锁外执行，不阻塞其他线程提交）─────────────────────
    data = _poll_fal(request_id, queue_base, headers, cfg, log)
    log(f"  ✓ {label} 成功  {len(data) // 1024}KB")
    return data, label
