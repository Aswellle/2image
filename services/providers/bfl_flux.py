"""
services/providers/bfl_flux.py — Black Forest Labs 官方 FLUX API（文生图 + 图生图）
提交: POST https://api.bfl.ai/v1/{model}
认证: Header x-key: <key>
响应: 提交返回 {id, polling_url}；轮询 polling_url 直到 status=="Ready"，
      图片地址在 result.sample（签名 URL，仅 10 分钟有效，需尽快下载）

文生图用 flux-pro-1.1（width/height/seed），
图生图用 flux-kontext-pro（input_image=base64 原图 + aspect_ratio，
不支持 width/height——由模型自动贴近参考图尺寸）。
"""
import base64
import threading
import time
import requests
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "id": "bfl_flux",
    "name": "💎 Black Forest Labs FLUX",
    "category": "paid",
    "config_key": "bfl_key",
    "supports_img2img": True,
}


_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 1.0

_BASE = "https://api.bfl.ai/v1"
_TIMEOUT = 30
_MAX_POLL = 60
_POLL_INTERVAL = 2.0

# aspect_ratio 供 flux-kontext-pro 使用（无 width/height 参数）
_ASPECTS = [
    (1/3, "3:7"), (3, "7:3"),
    (9/16, "9:16"), (16/9, "16:9"),
    (2/3, "2:3"), (3/2, "3:2"),
    (3/4, "3:4"), (4/3, "4:3"),
    (1, "1:1"),
]


def _best_aspect(w: int, h: int) -> str:
    r = w / max(h, 1)
    return min(_ASPECTS, key=lambda x: abs(x[0] - r))[1]


def try_bfl_flux(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("bfl_key", "").strip()
    if not key:
        raise ValueError("需要 Black Forest Labs API Key，请在「💎 付费接口配置」中填写")

    headers = {"x-key": key, "Content-Type": "application/json"}
    ref_image = cfg.get("_ref_image")   # bytes or None（图生图参考图）

    if ref_image is not None:
        model = "flux-kontext-pro"
        payload = {
            "prompt":       prompt,
            "input_image":  base64.b64encode(ref_image).decode("ascii"),
            "aspect_ratio": _best_aspect(w, h),
            "seed":         seed % 2_147_483_647,
        }
        log(f"► BFL {model}  图生图")
    else:
        # 文生图模型可通过 cfg["bfl_model"] 选择（默认 flux-pro-1.1，可选 FLUX.2 系列）
        model = cfg.get("bfl_model", "flux-pro-1.1")
        payload = {
            "prompt": prompt,
            "width":  max(256, min(1440, round(w / 32) * 32)),
            "height": max(256, min(1440, round(h / 32) * 32)),
            "seed":   seed % 2_147_483_647,
        }
        log(f"► BFL {model}  文生图  {payload['width']}×{payload['height']}")

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _session.post(f"{_BASE}/{model}", headers=headers,
                                 json=payload, timeout=_TIMEOUT)
        except requests.exceptions.ConnectionError as e:
            _LAST_DONE[0] = time.time()
            raise ValueError(f"无法连接 Black Forest Labs: {e}")
        _LAST_DONE[0] = time.time()

    if resp.status_code == 401:
        raise ValueError("Black Forest Labs API Key 无效")
    if resp.status_code == 402:
        raise ValueError("Black Forest Labs 账户余额不足")
    if resp.status_code == 429:
        raise ValueError("Black Forest Labs 速率限制，请稍后再试")
    if resp.status_code != 200:
        raise ValueError(f"BFL 提交失败 {resp.status_code}: {_safe_error_text(resp)}")

    j = resp.json()
    polling_url = j.get("polling_url", "")
    if not polling_url:
        raise ValueError(f"BFL 响应中无 polling_url：{j}")

    log(f"  任务 ID: {j.get('id', '?')}，开始轮询…")
    for i in range(_MAX_POLL):
        time.sleep(_POLL_INTERVAL)
        poll_resp = _session.get(polling_url, headers={"x-key": key}, timeout=_TIMEOUT)
        if poll_resp.status_code != 200:
            log(f"    轮询 {i+1}/{_MAX_POLL} 状态异常 {poll_resp.status_code}，继续等待…")
            continue

        pj = poll_resp.json()
        status = pj.get("status", "")
        log(f"    轮询 {i+1}/{_MAX_POLL}：{status}")

        if status == "Ready":
            img_url = pj.get("result", {}).get("sample", "")
            if not img_url:
                raise ValueError(f"BFL 任务完成但无图片 URL：{pj}")
            log("  下载图片中（签名 URL 仅 10 分钟有效）…")
            data = _safe_get_image(img_url, timeout=60)
            log(f"  ✓ BFL {model} 成功  {len(data)//1024}KB")
            return data, f"BFL/{model}"

        if status in ("Error", "Failed", "Request Moderated", "Content Moderated"):
            raise ValueError(f"BFL 任务失败：{pj.get('error', status)}")
        # Pending / Processing 继续轮询

    raise ValueError("BFL 任务轮询超时（120s）")
