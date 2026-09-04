"""
services/providers/openai_image.py — OpenAI GPT-Image（文生图 + 图生图）

FIX 2026-07: DALL-E 3 已于 2026-05-12 正式下线（OpenAI 官方弃用公告，
2025-11-14 发布），旧 openai_dalle.py 的 model="dall-e-3" 调用会直接
100% 失败。改用 gpt-image-1（可选 gpt-image-1-mini 省成本）。

UPDATE 2026-08: OpenAI 于 2026-04-21 发布 gpt-image-2（别名
gpt-image-2-2026-04-21），首个原生支持任意分辨率（WIDTHxHEIGHT）的图像模型。
本文件现同时支持 gpt-image-1 与 gpt-image-2，按 model 路由尺寸策略。

与 DALL-E 3 请求/响应的关键差异：
  · 不再有 response_format 参数——GPT-Image 系列固定返回 b64_json
  · quality 取值变为 low/medium/high/auto（原 standard/hd 已不适用）
  · size 取值变为 auto/1024x1024/1536x1024/1024x1536（gpt-image-2 额外支持
    2048x2048 / 2048x1152 / 3840x2160 / 2160x3840 及任意 WIDTHxHEIGHT）
  · 新增 /v1/images/edits 端点：传入参考图即可做图生图/局部编辑
  · 首次使用可能需要在 OpenAI 后台完成 Organization Verification，
    否则请求会被拒绝——这不是 API Key 本身的问题，遇到 403 需提示用户。
"""
import base64, math
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text

PROVIDER_INFO = {
    "id": "openai_image",
    "name": "💎 OpenAI GPT-Image",
    "category": "paid",
    "config_key": "openai_key",
    "supports_img2img": True,
}


# gpt-image-1 家族仅支持下列预设尺寸（取与请求最接近者）。
_SIZES = {(1024, 1024): "1024x1024", (1536, 1024): "1536x1024", (1024, 1536): "1024x1536"}

# gpt-image-2 任意尺寸约束（官方）：两边均为 16 的倍数；长边 ≤3840；
# 宽高比 1:3–3:1；总像素 0.65MP–8.3MP。
_GPT2_MULT = 16
_GPT2_LONG_MAX = 3840
_GPT2_MIN_PX = 655_360
_GPT2_MAX_PX = 8_294_400


def _best_size(w, h) -> str:
    return _SIZES[min(_SIZES.keys(), key=lambda s: abs(s[0] - w) + abs(s[1] - h))]


def _gpt2_size(w: int, h: int) -> str:
    """把请求的 w×h 映射为 gpt-image-2 接受的 WIDTHxHEIGHT。

    gpt-image-2 仅当满足「两边 16 的倍数 / 长边≤3840 / 宽高比 1:3–3:1 /
    0.65MP–8.3MP」时才接受任意尺寸；App 提供的小尺寸（512×512=0.26MP）与
    1920×1080（1080 非 16 倍数）必须在此收敛为合法值。保持 long/short 比例
    恒定，按像素上下限缩放后向 16 倍数取整（向上），保证不越界也不掉档。
    """
    ratio = min(3, max(w, h) / min(w, h))          # long/short, ≥1, ≤3
    long_e = min(max(w, h), _GPT2_LONG_MAX)
    short_e = long_e / ratio
    W, H = (long_e, short_e) if w >= h else (short_e, long_e)

    px = W * H
    if px < _GPT2_MIN_PX:
        s = (_GPT2_MIN_PX / px) ** 0.5
        W, H = W * s, H * s
    elif px > _GPT2_MAX_PX:
        s = (_GPT2_MAX_PX / px) ** 0.5
        W, H = W * s, H * s

    def up16(v): return max(_GPT2_MULT, math.ceil(v / _GPT2_MULT) * _GPT2_MULT)
    return f"{up16(W)}x{up16(H)}"


def _size_for(model: str, w: int, h: int) -> str:
    """按模型路由尺寸取值：gpt-image-2 家族用任意尺寸，其余用预设。"""
    if model.startswith("gpt-image-2"):
        return _gpt2_size(w, h)
    return _best_size(w, h)


def _normalize_quality(q: str) -> str:
    """把 DALL-E 时代的 standard/hd 归一化为 GPT-Image 体系值，其余原样。"""
    return {"standard": "medium", "hd": "high"}.get(q, q)


def try_openai_image(prompt, w, h, seed, cfg, log):
    key = cfg.get("openai_key", "").strip()
    if not key:
        raise ValueError("需要 OpenAI API Key，请在「💎 付费接口配置」中填写")

    model    = cfg.get("gpt_image_model", "gpt-image-1")
    # GPT-Image 系列 quality 只接受 auto/low/medium/high；把 DALL-E 时代的
    # standard/hd 旧配置归一化，避免 400（GPT-Image 不支持这两个值）。
    quality  = _normalize_quality(cfg.get("gpt_image_quality", "auto"))
    size_str = _size_for(model, w, h)
    ref_image = cfg.get("_ref_image")   # bytes or None（图生图参考图）

    headers = {"Authorization": f"Bearer {key}"}

    if ref_image is not None:
        # ── 图生图：/v1/images/edits，multipart/form-data ──────
        log(f"► OpenAI GPT-Image  图生图  质量={quality}  尺寸={size_str}")
        files = {"image": ("ref.png", ref_image, "image/png")}
        data = {"model": model, "prompt": prompt, "n": "1",
                "size": size_str, "quality": quality}
        resp = _session.post("https://api.openai.com/v1/images/edits",
            headers=headers, files=files, data=data, timeout=180)
    else:
        # ── 文生图：/v1/images/generations，JSON ────────────────
        log(f"► OpenAI GPT-Image  文生图  质量={quality}  尺寸={size_str}")
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
    log(f"  ✓ GPT-Image 成功 ({model}/{quality})")
    return base64.b64decode(b64), f"OpenAI/{model}-{quality}"
