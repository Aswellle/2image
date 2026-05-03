"""
services/providers/stability_ai.py
Stability AI — SDXL / SD3，支持 img2img
文生图端点: POST https://api.stability.ai/v1/generation/{engine}/text-to-image
图生图端点: POST https://api.stability.ai/v1/generation/{engine}/image-to-image
认证: Bearer Token
图生图 engine: stable-diffusion-xl-burn-2（推荐，支持度高）
"""
import base64, io, threading, time
from typing import Callable, Optional, Tuple
import requests
from PIL import Image

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 3.0
_TIMEOUT  = 120
_MAX_RETRIES = 3


def try_stability_ai(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    """
    Stability AI 文生图（已有逻辑，保持不变）。
    """
    key = cfg.get("stability_key", "").strip()
    if not key:
        raise ValueError("需要 Stability AI API Key！注册：https://platform.stability.ai/")

    engine_id = "stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {key}", "Accept": "image/*"}
    form = {
        "text_prompts[0][text]": prompt,
        "image_structure": "individual",
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Stability AI] 尝试 {attempt}/{_MAX_RETRIES}（{engine_id}）…")
                resp = requests.post(
                    f"https://api.stability.ai/v1/generation/{engine_id}/text-to-image",
                    headers=headers, data=form, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[Stability AI] 速率限制，等待 30s…")
                    time.sleep(30)
                    continue
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                _LAST_DONE[0] = time.time()
                log("[Stability AI] 生成成功 ✓")
                return (resp.content, f"StabilityAI/{engine_id}")
            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[Stability AI] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                log(f"[Stability AI] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Stability AI 全部重试失败：{last_err}")


def try_stability_img2img(
    prompt: str,
    w: int,
    h: int,
    seed: Optional[int],
    source_bytes: bytes,
    cfg: dict,
    log: Callable,
    strength: float = 0.7,
) -> Tuple[bytes, str]:
    """
    Stability AI 图生图（新增）。
    使用 stable-diffusion-xl-burn-2 engine，通过 init_image + prompt + strength 控制。
    strength: 控制参考图影响程度（0.1=轻微变化 ~ 0.9=大幅改造），默认 0.7
    """
    key = cfg.get("stability_key", "").strip()
    if not key:
        raise ValueError("需要 Stability AI API Key！注册：https://platform.stability.ai/")

    engine_id = "stable-diffusion-xl-burn-2"

    # 确保参考图尺寸与目标尺寸接近，避免 API 抱怨
    try:
        src_img = Image.open(io.BytesIO(source_bytes))
        if src_img.mode != "RGB":
            src_img = src_img.convert("RGB")
        buf = io.BytesIO()
        src_img.save(buf, format="JPEG", quality=90)
        img_bytes_for_api = buf.getvalue()
    except Exception as e:
        raise ValueError(f"参考图处理失败：{e}")

    # Stability AI 使用 multipart/form-data
    fields = {
        "init_image": ("reference.jpg", img_bytes_for_api, "image/jpeg"),
        "text_prompts[0][text]": (None, prompt.encode("utf-8"), None),
        "image_strength": (None, str(round(strength, 3)).encode("utf-8"), None),
        "cfg_scale": (None, b"7.5"),
        "samples": (None, b"1"),
    }
    if seed and seed > 0:
        fields["seed"] = (None, str(seed).encode("utf-8"), None)

    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "image/*",
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Stability AI img2img] 尝试 {attempt}/{_MAX_RETRIES}（strength={strength}）…")
                resp = requests.post(
                    f"https://api.stability.ai/v1/generation/{engine_id}/image-to-image",
                    headers=headers, files=fields, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[Stability AI img2img] 速率限制，等待 30s…")
                    time.sleep(30)
                    continue
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                if not resp.content or len(resp.content) < 1024:
                    raise RuntimeError("返回内容过小，可能非图片")
                _LAST_DONE[0] = time.time()
                log(f"[Stability AI img2img] 生成成功 ✓（strength={strength}）")
                return (resp.content, f"StabilityAI/img2img({strength})")
            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[Stability AI img2img] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                log(f"[Stability AI img2img] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Stability AI img2img 全部重试失败：{last_err}")
