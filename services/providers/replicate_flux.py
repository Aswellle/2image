"""
services/providers/replicate_flux.py
Replicate — FLUX.1 Pro
端点: POST https://api.replicate.com/v1/predictions
认证: Bearer Token
"""
import base64, threading, time, uuid
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 3.0
_TIMEOUT  = 300
_MAX_RETRIES = 3

def try_replicate(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("replicate_key", "").strip()
    if not key:
        raise ValueError("需要 Replicate Token！获取：https://replicate.com/account/api-tokens")

    model_ver = cfg.get("replicate_model", "black-forest-labs/flux-1.1-pro")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": model_ver,
        "input": {
            "prompt": prompt,
            "aspect_ratio": f"{w}x{h}",
            "output_format": "png",
        }
    }
    if seed and seed > 0: payload["input"]["seed"] = seed

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Replicate] 提交 {attempt}/{_MAX_RETRIES}，模型：{model_ver}…")
                resp = requests.post(
                    "https://api.replicate.com/v1/predictions",
                    headers=headers, json=payload, timeout=30)
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                pred_url = resp.json().get("urls", {}).get("get", "")
                image_bytes = _poll(pred_url, headers, log)
                _LAST_DONE[0] = time.time()
                log("[Replicate] 生成成功 ✓")
                return (image_bytes, f"Replicate/{model_ver.split('/')[-1]}")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Replicate] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(10 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[Replicate] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(10 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Replicate 全部重试失败：{last_err}")

def try_replicate_img2img(
    prompt: str, w: int, h: int, seed: int,
    source_bytes: bytes, cfg: dict, log: Callable,
    strength: float = 0.7,
) -> Tuple[bytes, str]:
    """
    Replicate 图生图（img2img）。

    使用 Stability AI SDXL 模型：
      https://replicate.com/stability-ai/sdxl

    模型支持 init_image（参考图）+ strength 参数（变化强度）。
    注意：FLUX.1 系列（flux-1.1-pro / schnell）不支持 img2img，
    因此 img2img 专用 SDXL 而非 FLUX。

    参数：
        source_bytes 参考图原始字节
        strength     变化强度 0.1~1.0（默认 0.7）
                     0.1 = 轻微变化，0.5 = 中等，0.9 = 大幅改造
        cfg          配置字典（含 replicate_key）
    返回：
        (image_bytes, provider_name)
    """
    key = cfg.get("replicate_key", "").strip()
    if not key:
        raise ValueError("需要 Replicate Token！获取：https://replicate.com/account/api-tokens")

    # 图生图专用 SDXL 模型（非 FLUX，FLUX 不支持 img2img）
    model_ver = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dhd76c5152d4edef6596749c03bd"

    b64_image = base64.b64encode(source_bytes).decode()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": model_ver,
        "input": {
            "prompt": prompt,
            "negative_prompt": "blurry, low quality, watermark, text, logo",
            "image": f"data:image/jpeg;base64,{b64_image}",
            "strength": strength,   # 0.1=保留原图多，0.9=变化大
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "seed": seed if seed and seed > 0 else None,
            "output_format": "png",
        }
    }
    payload["input"] = {k: v for k, v in payload["input"].items() if v is not None}

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Replicate img2img] 提交 {attempt}/{_MAX_RETRIES}，模型：sdxl…")
                resp = requests.post(
                    "https://api.replicate.com/v1/predictions",
                    headers=headers, json=payload, timeout=30)
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                pred_url = resp.json().get("urls", {}).get("get", "")
                image_bytes = _poll(pred_url, headers, log)
                _LAST_DONE[0] = time.time()
                log("[Replicate img2img] 生成成功 ✓")
                return (image_bytes, "Replicate/SDXL-img2img")
            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[Replicate img2img] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(10 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                log(f"[Replicate img2img] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(10 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Replicate img2img 全部重试失败：{last_err}")


def _poll(pred_url, headers, log) -> bytes:
    for _ in range(60):
        time.sleep(5)
        resp = requests.get(pred_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            continue
        state = resp.json().get("status", "")
        if state == "succeeded":
            out = resp.json().get("output", [])
            if out and isinstance(out, list):
                url = out[0] if isinstance(out[0], str) else out[0].get("url", "")
                if url:
                    r = requests.get(url, timeout=60); r.raise_for_status()
                    return r.content
            raise RuntimeError(f"Replicate 完成但无图片 URL：{out}")
        elif state in ("starting", "processing"):
            log(f"[Replicate] 生成中… ({state})")
        else:
            raise RuntimeError(f"Replicate 异常状态：{state} — {resp.text[:200]}")
    raise RuntimeError("Replicate 轮询超时")
