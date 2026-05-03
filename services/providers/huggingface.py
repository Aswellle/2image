"""
services/providers/huggingface.py
HuggingFace Inference API — 备用
端点: POST https://api-inference.huggingface.co/models/{model}
认证: Bearer Token
"""
import threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 3.0
_DEFAULT_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_hf_inference(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    token = cfg.get("hf_token", "").strip()
    if not token:
        raise ValueError("需要 HuggingFace Token！"
                         "获取：https://huggingface.co/settings/tokens")

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": min(max(w, 256), 1024),
            "height": min(max(h, 256), 1024),
            "num_inference_steps": 25,
        }
    }
    if seed and seed > 0: payload["parameters"]["seed"] = seed

    model = _DEFAULT_MODEL

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[HuggingFace] 尝试 {attempt}/{_MAX_RETRIES}，模型：{model}…")
                resp = requests.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers=headers, json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[HuggingFace] 速率限制，等待 20s…"); time.sleep(20); continue
                if resp.status_code == 503:
                    raise RuntimeError(f"模型加载中（{resp.status_code}），HF 首次调用需等待模型下载")
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                _LAST_DONE[0] = time.time()
                log("[HuggingFace] 生成成功 ✓")
                return (resp.content, f"HF/{model.split('/')[-1]}")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[HuggingFace] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(5 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[HuggingFace] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(5 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"HuggingFace 全部重试失败：{last_err}")
