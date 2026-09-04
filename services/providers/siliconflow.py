"""
services/providers/siliconflow.py — 硅基流动接口  v3
──────────────────────────────────────────────────────
v3 变体高质量模式（variant_hq）：
  · 新增 SF_HQ_MODELS 列表，当 cfg["variant_hq"]=True 时优先使用
  · FLUX.1-dev：28步，guidance_scale=3.5，比 schnell 8步画质显著提升
  · SDXL-base (HQ)：steps=35，guidance=8.0，更丰富细节与对比度
  · 跳过低质量蒸馏快速模型（SDXL-Lightning/sdxl-turbo），确保变体质量
  · 标准模式保持原有参数不变
"""
import requests
import time
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, validate_image_url as _validate_image_url, safe_error_text as _safe_error_text, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "id": "siliconflow",
    "name": "硅基流动 SiliconFlow (★推荐)",
    "category": "free",
    "config_key": "sf_key",
}


# ── 标准模式：速度与质量平衡（单张生成）──────────────────────────
SF_STD_MODELS = [
    # (model_id,                                   max_sz, steps, use_guid, guidance)
    ("black-forest-labs/FLUX.1-schnell",             1024,  8,   False, 0.0),
    ("stabilityai/stable-diffusion-xl-base-1.0",     1024, 30,   True,  7.5),
    ("ByteDance/SDXL-Lightning",                     1024,  4,   False, 0.0),
    ("stabilityai/stable-diffusion-2-1",              768, 30,   True,  8.0),
    ("stabilityai/sdxl-turbo",                        512,  2,   False, 0.0),
]

# ── 高质量模式：变体批量生成专用（variant_hq=True）──────────────
# 原则：
#   1. FLUX.1-dev 28步 + guidance_scale=3.5 → 细节/纹理远优于 schnell
#   2. SDXL-base 35步 + guidance=8.0 → 更强提示词服从，更丰富层次感
#   3. 跳过 SDXL-Lightning（4步蒸馏）和 sdxl-turbo（1步蒸馏）
#      这两个模型是批量时质量下降的主要元凶（fallback 后被选中）
SF_HQ_MODELS = [
    # (model_id,                                   max_sz, steps, use_guid, guidance)
    ("black-forest-labs/FLUX.1-dev",                 1024, 28,   True,  3.5),   # 最高质量
    ("stabilityai/stable-diffusion-xl-base-1.0",     1024, 35,   True,  8.0),   # HQ SDXL
    ("stabilityai/stable-diffusion-2-1",              768, 35,   True,  8.5),   # HQ SD2.1
]

# 高质量负向提示词（HQ 模式追加，降低瑕疵率）
_HQ_NEGATIVE = (
    "blurry, low quality, low resolution, pixelated, noisy, grainy, "
    "distorted, deformed, ugly, bad anatomy, bad proportions, "
    "watermark, text, logo, signature, extra limbs, missing limbs, "
    "out of focus, overexposed, underexposed, flat lighting"
)


def try_siliconflow(prompt: str, w: int, h: int, seed: int,
                    cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("sf_key", "").strip()
    if not key:
        raise ValueError(
            "需要硅基流动 API Key！请在「⚙ 设置」中填写。\n"
            "注册地址：https://cloud.siliconflow.cn"
        )

    # 根据是否为高质量变体模式选择不同模型列表
    hq_mode = bool(cfg.get("variant_hq", False))
    model_list = SF_HQ_MODELS if hq_mode else SF_STD_MODELS
    mode_tag   = "HQ变体" if hq_mode else "标准"
    log(f"► 硅基流动 SiliconFlow（{mode_tag}模式）…")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }

    def snap(v, mx):
        return min(max(128, (v // 128) * 128), mx)

    for model_id, max_sz, steps, use_guid, guidance in model_list:
        sw, sh = snap(w, max_sz), snap(h, max_sz)
        log(f"  模型: {model_id.split('/')[-1]}  {sw}x{sh}  steps={steps}"
            + (f"  guidance={guidance}" if use_guid else ""))

        payload = {
            "model":               model_id,
            "prompt":              prompt,
            "image_size":          f"{sw}x{sh}",
            "batch_size":          1,
            "num_inference_steps": steps,
            "seed":                seed % 2_147_483_647,
        }
        if use_guid:
            payload["guidance_scale"] = guidance
        # HQ 模式追加负向提示词（SDXL 系支持，FLUX.1-dev 不支持，条件：use_guid）
        if hq_mode and use_guid and "flux" not in model_id.lower():
            payload["negative_prompt"] = _HQ_NEGATIVE

        try:
            resp = _session.post(
                "https://api.siliconflow.cn/v1/images/generations",
                headers=headers, json=payload, timeout=90
            )
        except requests.exceptions.ConnectionError as e:
            raise ValueError(f"无法连接硅基流动: {e}")

        log(f"    状态: {resp.status_code}")

        if resp.status_code == 401:
            raise ValueError("硅基流动 API Key 无效")
        if resp.status_code == 402:
            raise ValueError("硅基流动余额不足")
        if resp.status_code == 429:
            wait = 3 if hq_mode else 2
            log(f"    速率限制，等待 {wait}s…")
            time.sleep(wait)
            continue
        if resp.status_code in (400, 422):
            log("    参数错误，换模型…")
            continue
        if resp.status_code != 200:
            log(f"    {resp.status_code}，换模型…")
            continue

        j = resp.json()
        # 官方当前响应容器为 data[].url；images[] 为历史字段，留作兼容后备
        items = j.get("data") or j.get("images") or []
        if not items:
            log("    无图片，换模型…")
            continue
        img_url = items[0].get("url", "")
        if not img_url:
            log("    无 URL，换模型…")
            continue

        inf_time = j.get("timings", {}).get("inference", "?")
        log(f"  ✓ 成功，推理耗时 {inf_time}s，下载中…")
        data = _safe_get_image(img_url, timeout=60)
        return data, f"硅基流动/{model_id.split('/')[-1]}"

    raise ValueError("所有硅基流动免费模型均失败")
