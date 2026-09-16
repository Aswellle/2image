"""
services/providers/openai_image.py — OpenAI GPT-Image（文生图 + 图生图）

支持模型族：gpt-image-1 / 1-mini / 1.5 / 2 / 2.5-flare / 2.5-sunburst
- gpt-image-1 系列：仅支持预设尺寸（1024x1024 / 1536x1024 / 1024x1536）
- gpt-image-2+ 系列：支持任意 WIDTHxHEIGHT（16 的倍数，长边 ≤3840，宽高比 1:3–3:1）
- gpt-image-2.5-flare：快速高质量日常生图
- gpt-image-2.5-sunburst：最强图像生成与编辑

与 DALL-E 3 请求/响应的关键差异：
  · 不再有 response_format 参数——GPT-Image 系列固定返回 b64_json
  · quality 取值变为 low/medium/high/auto（原 standard/hd 已不适用）
  · size 取值因模型而异（见上方说明）
  · 新增 /v1/images/edits 端点：传入参考图即可做图生图/局部编辑
"""
import base64

from config.model_catalog import (
    GPT_IMAGE_1,
    GPT_IMAGE_2,
    GPT_IMAGE_25_FLARE,
    GPT_IMAGE_25_SUNBURST,
    GPT_IMAGE_MODELS,
    GPT_IMAGE_DEFAULT,
    GPT_IMAGE_NAMES,
    GPT_IMAGE_LEGACY,
)
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text

PROVIDER_INFO = {
    "id": "openai_image",
    "name": "OpenAI GPT-Image (付费)",
    "category": "paid",
    "config_key": "openai_key",
    "description": "GPT-Image 系列：1/1.5/2/2.5-flare/2.5-sunburst",
}

# gpt-image-1 家族仅支持下列预设尺寸（取与请求最接近者）。
_SIZES = {(1024, 1024): "1024x1024", (1536, 1024): "1536x1024", (1024, 1536): "1024x1536"}

# gpt-image-2+ 任意尺寸约束（官方）：两边均为 16 的倍数；长边 ≤3840；
# 宽高比 1:3–3:1；总像素 0.65MP–8.3MP。
_GPT2_MULT = 16
_GPT2_LONG_MAX = 3840
_GPT2_MIN_PX = 655_360
_GPT2_MAX_PX = 8_294_400


def _best_size(w, h) -> str:
    return _SIZES[min(_SIZES.keys(), key=lambda s: abs(s[0] - w) + abs(s[1] - h))]


def _gpt2_size(w: int, h: int) -> str:
    """把请求的 w×h 映射为 gpt-image-2+ 接受的 WIDTHxHEIGHT。

    约束：
      - 两边均为 16 的倍数
      - 长边 ≤3840
      - 宽高比 1:3–3:1
      - 总像素 0.65MP–8.3MP
    """
    def up16(v):
        return max(_GPT2_MULT, (v + _GPT2_MULT // 2) // _GPT2_MULT * _GPT2_MULT)

    # 先约束宽高比 1:3–3:1
    if w / h > 3:
        w = h * 3
    elif h / w > 3:
        h = w * 3

    # 先满足最小像素：先放大再取整，确保取整后仍 ≥ min
    px = w * h
    if px < _GPT2_MIN_PX:
        # 先向上取整到16的倍数，再验证像素；若仍不足则继续放大短边
        w, h = up16(w), up16(h)
        while w * h < _GPT2_MIN_PX:
            # 放大较短的一边（保持宽高比更接近原始请求）
            if w <= h:
                w = up16(w + _GPT2_MULT)
            else:
                h = up16(h + _GPT2_MULT)
            # 安全检查：如果长边超限则停止
            if max(w, h) > _GPT2_LONG_MAX:
                w, h = _GPT2_LONG_MAX, up16(_GPT2_LONG_MAX // 3)
                break
    else:
        w, h = up16(w), up16(h)

    # 约束长边 ≤3840，然后约束像素上限（可能需要多次迭代）
    for _ in range(5):  # 最多 5 次迭代确保收敛
        if max(w, h) > _GPT2_LONG_MAX:
            if w > h:
                scale = _GPT2_LONG_MAX / w
                w = _GPT2_LONG_MAX
                h = up16(int(h * scale))
            else:
                scale = _GPT2_LONG_MAX / h
                h = _GPT2_LONG_MAX
                w = up16(int(w * scale))
        if w * h > _GPT2_MAX_PX:
            scale = (_GPT2_MAX_PX / (w * h)) ** 0.5 * 0.99  # 稍微保守
            w = up16(int(w * scale))
            h = up16(int(h * scale))
        if max(w, h) <= _GPT2_LONG_MAX and w * h <= _GPT2_MAX_PX and w * h >= _GPT2_MIN_PX:
            break

    return f"{w}x{h}"

def _size_for(model: str, w: int, h: int) -> str:
    """按模型路由尺寸取值：gpt-image-2+ 家族用任意尺寸，其余用预设。"""
    if model in (GPT_IMAGE_2, GPT_IMAGE_25_FLARE, GPT_IMAGE_25_SUNBURST):
        return _gpt2_size(w, h)
    return _best_size(w, h)


def _normalize_quality(q: str) -> str:
    """把 DALL-E 时代的 standard/hd 归一化为 GPT-Image 体系值，其余原样。"""
    return {"standard": "medium", "hd": "high"}.get(q, q)


def try_openai_image(prompt, w, h, seed, cfg, log):
    key = cfg.get("openai_key", "").strip()
    if not key:
        raise ValueError("需要 OpenAI API Key，请在「💎 付费接口配置」中填写")

    model = cfg.get("gpt_image_model", GPT_IMAGE_DEFAULT)
    quality = _normalize_quality(cfg.get("gpt_image_quality", "auto"))
    size_str = _size_for(model, w, h)
    ref_image = cfg.get("_ref_image")

    headers = {"Authorization": f"Bearer {key}"}

    if ref_image is not None:
        log(f"► OpenAI GPT-Image  图生图  质量={quality}  尺寸={size_str}")
        files = {"image": ("ref.png", ref_image, "image/png")}
        data = {"model": model, "prompt": prompt, "n": "1",
                "size": size_str, "quality": quality}
        resp = _session.post("https://api.openai.com/v1/images/edits",
            headers=headers, files=files, data=data, timeout=180)
    else:
        log(f"► OpenAI GPT-Image  文生图  模型={GPT_IMAGE_NAMES.get(model, model)}  质量={quality}  尺寸={size_str}")
        resp = _session.post("https://api.openai.com/v1/images/generations",
            headers={**headers, "Content-Type": "application/json"},
            json={"model": model, "prompt": prompt, "n": 1,
                  "size": size_str, "quality": quality}, timeout=120)

    log(f"  状态: {resp.status_code}")
    if resp.status_code == 401:
        raise ValueError("OpenAI API Key 无效或已过期")
    if resp.status_code == 402:
        raise ValueError("OpenAI 账户余额不足")
    if resp.status_code == 403:
        raise ValueError(
            "OpenAI 拒绝访问 GPT-Image——首次使用该模型可能需要先在 "
            "platform.openai.com 后台完成 Organization Verification（组织验证）")
    if resp.status_code == 429:
        raise ValueError("OpenAI 速率限制")
    if resp.status_code == 400:
        raise ValueError(f"GPT-Image 请求错误: {resp.json().get('error',{}).get('message','')}")
    if resp.status_code != 200:
        raise ValueError(f"OpenAI 返回 {resp.status_code}: {_safe_error_text(resp)}")

    j = resp.json()
    b64 = j["data"][0].get("b64_json", "")
    if not b64:
        raise ValueError("GPT-Image 返回数据中无图片")
    display_name = GPT_IMAGE_NAMES.get(model, model)
    log(f"  ✓ GPT-Image 成功 ({display_name}/{quality})")
    return base64.b64decode(b64), f"OpenAI/{display_name}-{quality}"
