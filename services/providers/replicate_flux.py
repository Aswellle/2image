"""
services/providers/replicate_flux.py
Replicate — FLUX.1 Pro
端点: POST https://api.replicate.com/v1/predictions
认证: Bearer Token
"""
import threading, time, uuid
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
