"""
services/providers/leonardoai.py
Leonardo.ai — 专注 AI 艺术创作，社区模型丰富
端点: POST https://cloud.leonardo.ai/api/rest/v1/generations
认证: Bearer Token (User OAuth)
响应: {sdGenerationJob: {generationId: "..."}}
轮询: GET https://cloud.leonardo.ai/api/rest/v1/generations/{id}
免费: 150 tokens/天，$10/月起
"""
import base64, threading, time
from typing import Callable, Tuple
import requests

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0
_TIMEOUT  = 120
_MAX_RETRIES = 3

def try_leonardo(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    key = cfg.get("leonardo_key", "").strip()
    if not key:
        raise ValueError("需要 Leonardo.ai API Key！注册：https://app.leonardo.ai/"
                         "（$10/月起，150 tokens/天免费）")

    model_id = cfg.get("leonardo_model_id", "6b53d33e-4c6e-47e5-afd8-9d66a8e31b5f")  # DreamShaper
    preset   = cfg.get("leonardo_preset", "DREAMSHAPER_COOKIE")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, watermark, text, logo, deformed",
        "width": min(max(w, 512), 1024),
        "height": min(max(h, 512), 1024),
        "num_images": 1,
        "model_id": model_id,
        "prompt_magic": True,
        "guidance_scale": 7.5,
        "style_uuid": preset,
    }
    if seed and seed > 0: payload["seed"] = seed

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV: time.sleep(_MIN_INTV - gap)
        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Leonardo.ai] 提交 {attempt}/{_MAX_RETRIES}（模型：{model_id[:8]}…）…")
                resp = requests.post(
                    "https://cloud.leonardo.ai/api/rest/v1/generations",
                    headers=headers, json=payload, timeout=_TIMEOUT)
                if resp.status_code == 429:
                    log("[Leonardo.ai] 速率限制，等待 30s…"); time.sleep(30); continue
                if resp.status_code == 401:
                    raise ValueError("Leonardo.ai Token 无效，请前往 https://app.leonardo.ai/account 重新生成。")
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                gen_id = resp.json().get("sdGenerationJob", {}).get("generationId", "")
                if not gen_id:
                    raise ValueError(f"Leonardo.ai 未返回 generationId：{resp.json()}")
                log(f"[Leonardo.ai] 任务ID：{gen_id}，等待生成（可长达60s）…")
                image_bytes = _poll(gen_id, headers, log)
                _LAST_DONE[0] = time.time()
                log("[Leonardo.ai] 生成成功 ✓")
                return (image_bytes, f"Leonardo/{model_id[:8]}")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Leonardo.ai] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(10 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[Leonardo.ai] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(10 * attempt)
        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Leonardo.ai 全部重试失败：{last_err}")

def _poll(gen_id, headers, log) -> bytes:
    for i in range(36):   # 最多 3 分钟
        time.sleep(5)
        resp = requests.get(
            f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}",
            headers=headers, timeout=30)
        if resp.status_code != 200:
            continue
        data = resp.json()
        status = data.get("generations_by_pk", {}).get("status", "")
        if status == "COMPLETE":
            images = data["generations_by_pk"].get("generated_images", [])
            if not images:
                raise RuntimeError("Leonardo.ai 完成但无图片")
            url = images[0].get("url", "")
            if url:
                log(f"[Leonardo.ai] 下载图片：{url[:80]}…")
                r = requests.get(url, timeout=60); r.raise_for_status()
                return r.content
            raise RuntimeError("Leonardo.ai 完成的图片无 URL")
        elif status in ("PENDING", "PROCESSING"):
            log(f"[Leonardo.ai] 生成中…（{i*5}s）")
        else:
            raise RuntimeError(f"Leonardo.ai 异常状态：{status}")
    raise RuntimeError("Leonardo.ai 轮询超时（3分钟）")
