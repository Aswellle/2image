"""services/providers/stability_ai.py — Stability AI（文生图 + 图生图）"""
import base64
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text

PROVIDER_INFO = {
    "name": "💎 Stability AI",
    "category": "paid",
    "config_key": "stability_key",
}


_ASPECT = {(1024,1024):"1:1",(1344,768):"16:9",(768,1344):"9:16",
           (1216,832):"3:2",(832,1216):"2:3",(1152,896):"4:3",
           (896,1152):"3:4",(1536,640):"21:9"}
_EP = {"core":"https://api.stability.ai/v2beta/stable-image/generate/core",
       "ultra":"https://api.stability.ai/v2beta/stable-image/generate/ultra",
       "sd3.5-large":"https://api.stability.ai/v2beta/stable-image/generate/sd3"}
# img2img 仅 SD3 端点支持
_EP_IMG2IMG = "https://api.stability.ai/v2beta/stable-image/generate/sd3"


def _aspect(w,h):
    r = w/max(h,1)
    return _ASPECT[min(_ASPECT.keys(), key=lambda s: abs(s[0]/s[1]-r))]


def _parse_response(resp, model, log):
    """解析 Stability AI 响应（直接图片 or JSON base64）。"""
    if "image" in resp.headers.get("Content-Type",""):
        log(f"  ✓ Stability AI {model} 成功")
        return resp.content, f"StabilityAI/{model}"
    try:
        j = resp.json()
        for item in (j.get("artifacts") or j.get("images") or []):
            b64 = item.get("base64") or item.get("image")
            if b64:
                log(f"  ✓ Stability AI {model} 成功（JSON）")
                return base64.b64decode(b64), f"StabilityAI/{model}"
    except Exception:
        pass
    raise ValueError("Stability AI 响应格式未知")


def try_stability_ai(prompt, w, h, seed, cfg, log):
    key = cfg.get("stability_key","").strip()
    if not key: raise ValueError("需要 Stability AI API Key，请在「💎 付费接口配置」中填写")

    ref_image = cfg.get("_ref_image")        # bytes or None
    strength  = cfg.get("_ref_strength", 0.6)
    headers   = {"Authorization": f"Bearer {key}", "Accept": "image/*"}

    if ref_image is not None:
        # ── 图生图模式：使用 SD3 端点，mode=image-to-image ──────
        log(f"► Stability AI SD3  图生图  强度={strength:.1f}")
        files = {
            "image":         ("init.png", ref_image, "image/png"),
            "prompt":        (None, prompt),
            "mode":          (None, "image-to-image"),
            "strength":      (None, f"{strength:.2f}"),
            "model":         (None, "sd3.5-large"),
            "output_format": (None, "png"),
            "seed":          (None, str(seed % 4294967294)),
        }
        resp = _session.post(_EP_IMG2IMG, headers=headers, files=files, timeout=150)
    else:
        # ── 文生图模式（原逻辑）──────────────────────────────────
        model = cfg.get("stability_model","core")
        aspect = _aspect(w,h)
        url = _EP.get(model, _EP["core"])
        log(f"► Stability AI  模型={model}  宽高比={aspect}")
        data = {"prompt":prompt,"aspect_ratio":aspect,"output_format":"png","seed":str(seed%4294967294)}
        if model == "sd3.5-large": data["model"] = "sd3.5-large"
        resp = _session.post(url, headers=headers,
                             files={k:(None,v) for k,v in data.items()}, timeout=120)

    log(f"  状态: {resp.status_code}")
    if resp.status_code == 401: raise ValueError("Stability AI Key 无效或已过期")
    if resp.status_code == 402: raise ValueError("Stability AI 余额不足")
    if resp.status_code == 422: raise ValueError(f"Stability AI 参数错误: {_safe_error_text(resp)}")
    if resp.status_code != 200: raise ValueError(f"Stability AI 返回 {resp.status_code}: {_safe_error_text(resp)}")

    model_tag = "sd3.5-large(img2img)" if ref_image else cfg.get("stability_model","core")
    return _parse_response(resp, model_tag, log)
