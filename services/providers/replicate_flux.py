"""services/providers/replicate_flux.py — Replicate FLUX（文生图）

2026-11 对照 replicate.com 官方模型页内嵌 Input schema 校准：
  · flux-2-pro：aspect_ratio=custom 时才使用 width/height（256–2048、
    16 的倍数）；无 num_outputs 字段；image_input 支持最多 8 张参考图
    （本 provider 暂只做文生图）
  · flux-1.1-pro：width/height 同样仅 aspect_ratio=custom 生效
    （256–1440、32 的倍数）；无 num_outputs
  · flux-pro / flux-dev（FLUX 1.0）：width/height/steps/guidance 直传

此前对所有模型统一发 width/height/num_outputs——width/height 因
aspect_ratio 未设 custom 被忽略（出图恒 1:1），num_outputs 字段
根本不存在于 1.1-pro / 2-pro 的 schema。
"""

import base64
import time

from services.generation.errors import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderInvalidResponseError,
    ProviderQuotaError,
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
    "id": "replicate_flux",
    "name": "💎 Replicate FLUX",
    "category": "paid",
    "config_key": "replicate_key",
    "try_fn": "try_replicate",
}


_MODELS = {
    "flux-2-pro": "black-forest-labs/flux-2-pro",
    "flux-1.1-pro": "black-forest-labs/flux-1.1-pro",
    "flux-pro": "black-forest-labs/flux-pro",
    "flux-dev": "black-forest-labs/flux-dev",
}

# 下拉可见顺序（官方在册的 FLUX.2 Pro 为默认，1.x 为 legacy）
MODEL_ORDER = ["flux-2-pro", "flux-1.1-pro", "flux-pro", "flux-dev"]

_FLUX2_DIMS = (256, 2048, 16)  # min, max, multiple
_FLUX1_PRO_DIMS = (256, 1440, 32)


def _clamp(w: int, h: int, lo: int, hi: int, mult: int) -> tuple[int, int]:
    cw = max(lo, min(hi, round(w / mult) * mult))
    ch = max(lo, min(hi, round(h / mult) * mult))
    return cw, ch


def _build_input(slug: str, prompt: str, w: int, h: int, seed: int) -> dict:
    """按各模型官方 schema 构造 input。"""
    seed = seed % 2147483647
    if slug == "flux-2-pro":
        cw, ch = _clamp(w, h, *_FLUX2_DIMS)
        return {
            "prompt": prompt,
            "aspect_ratio": "custom",
            "width": cw,
            "height": ch,
            "output_format": "png",
            "seed": seed,
        }
    if slug == "flux-1.1-pro":
        cw, ch = _clamp(w, h, *_FLUX1_PRO_DIMS)
        return {
            "prompt": prompt,
            "aspect_ratio": "custom",
            "width": cw,
            "height": ch,
            "output_format": "png",
            "seed": seed,
        }
    # FLUX 1.0 pro/dev：width/height/steps/guidance 直传
    body = {
        "prompt": prompt,
        "width": max(256, min(1440, round(w / 32) * 32)),
        "height": max(256, min(1440, round(h / 32) * 32)),
        "output_format": "png",
        "seed": seed,
    }
    if slug == "flux-dev":
        body.update({"num_inference_steps": 28, "guidance_scale": 3.5})
    return body


def try_replicate(prompt, w, h, seed, cfg, log):
    key = cfg.get("replicate_key", "").strip()
    if not key:
        raise ProviderConfigError("需要 Replicate API Token，请在「💎 付费接口配置」中填写")
    slug = cfg.get("replicate_model", "flux-2-pro")
    if slug not in _MODELS:
        # 下拉为只读，目录外值（含旧下拉无效项与空值）归一化到默认
        if slug:
            log(f"[Replicate] 模型 {slug!r} 不在注册表，已归一化到默认 flux-2-pro")
        slug = "flux-2-pro"
    path = _MODELS[slug]
    body_input = _build_input(slug, prompt, w, h, seed)
    log(f"► Replicate  模型={path}  {body_input.get('width', '?')}×{body_input.get('height', '?')}")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "wait"}
    resp = _get_session().post(
        f"https://api.replicate.com/v1/models/{path}/predictions",
        headers=headers,
        json={"input": body_input},
        timeout=90,
    )
    log(f"  状态: {resp.status_code}")
    if resp.status_code == 401:
        raise ProviderAuthError("Replicate Token 无效")
    if resp.status_code == 402:
        raise ProviderQuotaError("Replicate 余额不足")
    if resp.status_code not in (200, 201):
        raise classify_http_error(resp.status_code, f"Replicate 返回 {resp.status_code}: {_safe_error_text(resp)}")
    j = resp.json()
    pred_id = j.get("id")
    status = j.get("status", "")
    output = j.get("output")
    if status != "succeeded" and pred_id:
        log(f"  轮询中（id={pred_id[:8]}）…")
        for i in range(40):
            _raise_if_cancelled(cfg)
            time.sleep(3)
            pr = _get_session().get(
                f"https://api.replicate.com/v1/predictions/{pred_id}",
                headers={"Authorization": f"Bearer {key}"},
                timeout=20,
            )
            pr.raise_for_status()
            pj = pr.json()
            status = pj.get("status", "")
            log(f"  [{i + 1}/40] status={status}")
            if status == "succeeded":
                output = pj.get("output")
                break
            if status in ("failed", "canceled"):
                raise ProviderInvalidResponseError(f"Replicate 任务失败: {pj.get('error', '')}")
        else:
            raise ProviderTransientError("Replicate 120s 超时")
    if isinstance(output, list) and output:
        img_url = output[0]
    elif isinstance(output, str):
        img_url = output
    else:
        raise ProviderInvalidResponseError(f"Replicate 输出格式未知: {output}")
    if img_url.startswith("data:"):
        log(f"  ✓ Replicate {slug} 成功（data URI）")
        return base64.b64decode(img_url.split(",", 1)[1]), f"Replicate/{slug}"
    log(f"  下载图片: {img_url[:60]}…")
    data = _safe_get_image(img_url, timeout=60)
    log(f"  ✓ Replicate {slug} 成功")
    return data, f"Replicate/{slug}"
