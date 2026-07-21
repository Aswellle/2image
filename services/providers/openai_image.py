"""
services/providers/openai_image.py — OpenAI GPT-Image（文生图 + 图生图）

FIX 2026-07: DALL-E 3 已于 2026-05-12 正式下线（OpenAI 官方弃用公告，
2025-11-14 发布），旧 openai_dalle.py 的 model="dall-e-3" 调用会直接
100% 失败。改用 gpt-image-1（可选 gpt-image-1-mini 省成本）。

与 DALL-E 3 请求/响应的关键差异：
  · 不再有 response_format 参数——GPT-Image 系列固定返回 b64_json
  · quality 取值变为 low/medium/high/auto（原 standard/hd 已不适用）
  · size 取值变为 auto/1024x1024/1536x1024/1024x1536
  · 新增 /v1/images/edits 端点：传入参考图即可做图生图/局部编辑
  · 首次使用可能需要在 OpenAI 后台完成 Organization Verification，
    否则请求会被拒绝——这不是 API Key 本身的问题，遇到 403 需提示用户。
"""
import base64
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text

PROVIDER_INFO = {
    "id": "openai_image",
    "name": "💎 OpenAI GPT-Image",
    "category": "paid",
    "config_key": "openai_key",
    "supports_img2img": True,
}


_SIZES = {(1024, 1024): "1024x1024", (1536, 1024): "1536x1024", (1024, 1536): "1024x1536"}


def _best_size(w, h) -> str:
    return _SIZES[min(_SIZES.keys(), key=lambda s: abs(s[0] - w) + abs(s[1] - h))]


def try_openai_image(prompt, w, h, seed, cfg, log):
    key = cfg.get("openai_key", "").strip()
    if not key:
        raise ValueError("需要 OpenAI API Key，请在「💎 付费接口配置」中填写")

    model    = cfg.get("gpt_image_model", "gpt-image-1")
    quality  = cfg.get("gpt_image_quality", "auto")   # low | medium | high | auto
    size_str = _best_size(w, h)
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
