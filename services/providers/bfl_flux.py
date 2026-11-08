"""
services/providers/bfl_flux.py — Black Forest Labs 官方 FLUX API（文生图 + 图生图）
提交: POST https://api.bfl.ai/v1/{model}
认证: Header x-key: <key>
响应: 提交返回 {id, polling_url}；轮询 polling_url 直到 status=="Ready"，
      图片地址在 result.sample（签名 URL，仅 10 分钟有效，需尽快下载）

FLUX.2 时代（2026-11 对照 docs.bfl.ml 核实）：
  · /v1/flux-2-pro 为官方推荐默认端点，同一端点承担生成与编辑——
    编辑即带 input_image（最多 8 张，base64 或 URL）
  · 文生图模型由 cfg["bfl_model"] 从目录选择（flux-2-pro 默认，
    可选 flux-2-pro-preview / flux-2-max / flux-2-flex / flux-pro-1.1）
  · 图生图：配置为 FLUX.2 家族时直接带参考图编辑；配置为不支持
    编辑输入的 flux-pro-1.1 时自动改走 flux-2-pro（官方编辑推荐端点）
"""

import base64
import threading
import time
from typing import Callable, Tuple

import requests

from config.model_catalog import BFL_FLUX2_PRO, BFL_TXT2IMG_DEFAULT, BFL_TXT2IMG_MODELS
from services.generation.errors import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderInvalidResponseError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderTransientError,
    classify_http_error,
)
from services.providers._net import (
    get_session as _get_session,
)
from services.providers._net import (
    raise_if_cancelled as _raise_if_cancelled,
)
from services.providers._net import (
    safe_error_text as _safe_error_text,
)
from services.providers._net import (
    safe_get_image as _safe_get_image,
)

PROVIDER_INFO = {
    "id": "bfl_flux",
    "name": "💎 Black Forest Labs FLUX",
    "category": "paid",
    "config_key": "bfl_key",
    "supports_img2img": True,
}


_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 1.0

_BASE = "https://api.bfl.ai/v1"
_TIMEOUT = 30
_MAX_POLL = 60
_POLL_INTERVAL = 2.0


def _clamp_dims(w: int, h: int) -> tuple[int, int]:
    """钳制到 BFL 接受的范围（≥256、32 的倍数，长边 ≤1440）。"""
    cw = max(256, min(1440, round(w / 32) * 32))
    ch = max(256, min(1440, round(h / 32) * 32))
    return cw, ch


def try_bfl_flux(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("bfl_key", "").strip()
    if not key:
        raise ProviderConfigError("需要 Black Forest Labs API Key，请在「💎 付费接口配置」中填写")

    headers = {"x-key": key, "Content-Type": "application/json"}
    ref_image = cfg.get("_ref_image")  # bytes or None（图生图参考图）

    model = cfg.get("bfl_model", "").strip()
    if model not in BFL_TXT2IMG_MODELS:
        # 下拉为只读，目录外值与空值都归一化到目录默认
        if model:
            log(f"[BFL] 模型 {model!r} 不在目录，已归一化到默认 {BFL_TXT2IMG_DEFAULT}")
        model = BFL_TXT2IMG_DEFAULT
    cw, ch = _clamp_dims(w, h)

    if ref_image is not None and model != BFL_FLUX2_PRO:
        # 编辑输入（input_image）仅对 FLUX.2 [pro] 逐项验证过；1.1 Pro 不
        # 接受编辑输入，2-max/2-flex/2-pro-preview 未验证——图生图一律
        # 改走官方推荐的 FLUX.2 [pro] 编辑端点
        model = BFL_FLUX2_PRO

    payload = {
        "prompt": prompt,
        "width": cw,
        "height": ch,
        "seed": seed % 2_147_483_647,
        "output_format": "png",
    }
    if ref_image is not None:
        payload["input_image"] = base64.b64encode(ref_image).decode("ascii")
        log(f"► BFL {model}  图生图  {cw}×{ch}")
    else:
        log(f"► BFL {model}  文生图  {cw}×{ch}")

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _get_session().post(f"{_BASE}/{model}", headers=headers, json=payload, timeout=_TIMEOUT)
        except requests.exceptions.ConnectionError as e:
            _LAST_DONE[0] = time.time()
            raise ProviderTransientError(f"无法连接 Black Forest Labs: {e}")
        _LAST_DONE[0] = time.time()

    if resp.status_code == 401:
        raise ProviderAuthError("Black Forest Labs API Key 无效")
    if resp.status_code == 402:
        raise ProviderQuotaError("Black Forest Labs 账户余额不足")
    if resp.status_code == 429:
        raise ProviderRateLimitError("Black Forest Labs 速率限制（HTTP 429），请稍后再试")
    if resp.status_code != 200:
        raise classify_http_error(resp.status_code, f"BFL 提交失败 {resp.status_code}: {_safe_error_text(resp)}")

    j = resp.json()
    polling_url = j.get("polling_url", "")
    if not polling_url:
        raise ProviderInvalidResponseError(f"BFL 响应中无 polling_url：{j}")

    log(f"  任务 ID: {j.get('id', '?')}，开始轮询…")
    for i in range(_MAX_POLL):
        _raise_if_cancelled(cfg)
        time.sleep(_POLL_INTERVAL)
        poll_resp = _get_session().get(polling_url, headers={"x-key": key}, timeout=_TIMEOUT)
        if poll_resp.status_code != 200:
            log(f"    轮询 {i + 1}/{_MAX_POLL} 状态异常 {poll_resp.status_code}，继续等待…")
            continue

        pj = poll_resp.json()
        status = pj.get("status", "")
        log(f"    轮询 {i + 1}/{_MAX_POLL}：{status}")

        if status == "Ready":
            img_url = pj.get("result", {}).get("sample", "")
            if not img_url:
                raise ProviderInvalidResponseError(f"BFL 任务完成但无图片 URL：{pj}")
            log("  下载图片中（签名 URL 仅 10 分钟有效）…")
            data = _safe_get_image(img_url, timeout=60)
            log(f"  ✓ BFL {model} 成功  {len(data) // 1024}KB")
            return data, f"BFL/{model}"

        if status in ("Error", "Failed", "Request Moderated", "Content Moderated"):
            raise ProviderInvalidResponseError(f"BFL 任务失败：{pj.get('error', status)}")
        # Pending / Processing 继续轮询

    raise ProviderTransientError("BFL 任务轮询超时（120s）")
