"""
services/providers/stablehorde.py
StableHorde — 分布式算力网络，完全免费（匿名可跑）
端点: POST https://stablehorde.net/api/v2/generate/async
认证: API Key（可选，匿名限速更严）
"""
import base64, threading, time, uuid
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 3.0
_TIMEOUT  = 300
_MAX_RETRIES = 3

def try_stablehorde(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("stablehorde_key", "").strip() or None
    headers = {"Content-Type": "application/json", "Client-Agent": "2image/1.0"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    payload = {
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, watermark, text, logo",
        "width": min(max(w, 256), 1024),
        "height": min(max(h, 256), 1024),
        "steps": 25,
        "n": 1,
        "model_id": "stable_diffusion",
    }
    if seed and seed > 0: payload["seed"] = seed

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[StableHorde] 提交任务 {attempt}/{_MAX_RETRIES}…")
                # 步骤1：提交生成请求
                resp = requests.post(
                    "https://stablehorde.net/api/v2/generate/async",
                    headers=headers, json=payload, timeout=30)
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                job_id = resp.json().get("id")
                log(f"[StableHorde] 任务ID：{job_id}，等待生成…")

                # 步骤2：轮询等待完成
                image_bytes = _wait_and_fetch(job_id, headers, log)
                _LAST_DONE[0] = time.time()
                log("[StableHorde] 生成成功 ✓")
                return (image_bytes, "StableHorde/SD")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[StableHorde] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(10 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[StableHorde] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(10 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"StableHorde 全部重试失败：{last_err}")

def _wait_and_fetch(job_id, headers, log) -> bytes:
    poll_url = f"https://stablehorde.net/api/v2/generate/status/{job_id}"
    for _ in range(60):
        time.sleep(5)
        resp = requests.get(poll_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            continue
        state = resp.json()
        status = state.get("status", "")
        if status == "completed":
            gen = state.get("generations", [])
            if not gen:
                raise RuntimeError("StableHorde 完成但无图片数据")
            b64 = gen[0].get("img2img_base64", "") or gen[0].get("base64", "")
            if b64:
                return base64.b64decode(b64)
            url = gen[0].get("img2img_url", "") or gen[0].get("url", "")
            if url:
                r = requests.get(url, timeout=60); r.raise_for_status()
                return r.content
            raise RuntimeError("StableHorde 完成的图片既无 base64 也无 URL")
        elif status in ("waiting", "processing"):
            done = state.get("finished", 0)
            total = state.get("steps", 1)
            log(f"[StableHorde] 生成中… {done}/{total}")
        else:
            raise RuntimeError(f"StableHorde 状态异常：{status}")
    raise RuntimeError("StableHorde 轮询超时（5分钟）")
