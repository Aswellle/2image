"""
services/providers/modelslab.py
ModelsLab — 免费 100次/天，支持 img2img
端点: POST https://api.modelslab.com/v3/images/text2img
认证: API Key
响应: {data:[{image: "base64..."}]}
"""
import base64, threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0
_ENDPOINT  = "https://api.modelslab.com/v3/images/text2img"
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_modelslab(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("modelslab_key", "").strip()
    if not key:
        raise ValueError("需要 ModelsLab API Key！注册：https://modelslab.com/")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model_version": 5,
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, watermark",
        "width": min(max(w, 256), 1280),
        "height": min(max(h, 256), 1280),
        "num_inference_steps": 30,
        "seed": seed if seed and seed > 0 else None,
        "guidance_scale": 7.5,
        "webhook": None,
        "track_id": None,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[ModelsLab] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = requests.post(_ENDPOINT, headers=headers,
                                    json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[ModelsLab] 速率限制，等待 30s…"); time.sleep(30); continue
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log("[ModelsLab] 生成成功 ✓")
                return (image_bytes, "ModelsLab")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[ModelsLab] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[ModelsLab] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"ModelsLab 全部重试失败：{last_err}")

def _extract_image(data, log) -> bytes:
    imgs = data.get("data", [])
    if not imgs:
        raise ValueError(f"ModelsLab 响应无 data：{data}")
    b64 = imgs[0].get("image", "")
    if b64:
        return base64.b64decode(b64)
    raise ValueError(f"ModelsLab 响应无 image 字段")


def try_modelslab_img2img(prompt, w, h, seed, source_bytes, cfg, log,
                          strength: float = None,
                          control_mode: str = "none",
                          ) -> Tuple[bytes, str]:
    """ModelsLab 图生图（strength 参数预留，Pollinations 兼容）。
    control_mode 参数：ModelsLab 不支持 ControlNet，此参数会被忽略。
    """
    key = cfg.get("modelslab_key", "").strip()
    if not key:
        raise ValueError("需要 ModelsLab API Key！")

    b64 = base64.b64encode(source_bytes).decode()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model_version": 5,
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, watermark",
        "width": min(max(w, 256), 1280),
        "height": min(max(h, 256), 1280),
        "num_inference_steps": 30,
        "seed": seed if seed and seed > 0 else None,
        "init_image": f"data:image/jpeg;base64,{b64}",
        "strength": 0.7,
        "guidance_scale": 7.5,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[ModelsLab img2img] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = requests.post(
                    "https://api.modelslab.com/v3/images/img2img",
                    headers=headers, json=payload, timeout=_TIMEOUT)
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                image_bytes = _extract_image(resp.json(), log)
                _LAST_DONE[0] = time.time()
                log("[ModelsLab img2img] 生成成功 ✓")
                return (image_bytes, "ModelsLab/img2img")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[ModelsLab img2img] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                if attempt < _MAX_RETRIES: time.sleep(3 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"ModelsLab img2img 全部重试失败：{last_err}")
