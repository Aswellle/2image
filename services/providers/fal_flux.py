"""
services/providers/fal_flux.py — fal.ai FLUX（文生图 + 图生图）
· 文生图: fal-ai/flux-pro/v1.1-ultra（最高写实质量，4MP）
· 图生图: fal-ai/flux-general/image-to-image（FLUX 风格迁移）
API 均为队列提交 + 轮询模式
Key: Header  Authorization: Key <key>
"""
import base64
import threading
import time
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, validate_image_url as _validate_image_url, safe_error_text as _safe_error_text, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "name": "fal.ai FLUX Ultra (高质量)",
    "category": "commercial",
    "config_key": "fal_key",
}


_LOCK        = threading.Lock()
_LAST_DONE   = [0.0]
_MIN_INTV    = 3.0    # 提交间隔
_POLL_SEC    = 3.0    # 轮询间隔
_MAX_POLLS   = 40     # 最多等 120s

_QUEUE_T2I   = "https://queue.fal.run/fal-ai/flux-pro/v1.1-ultra"
_QUEUE_I2I   = "https://queue.fal.run/fal-ai/flux-general/image-to-image"
_QUEUE_BASE  = _QUEUE_T2I  # 向后兼容

_ASPECTS = [
    ((1024, 1024), "1:1"),
    ((1344,  768), "16:9"),
    (( 768, 1344), "9:16"),
    ((1216,  832), "3:2"),
    (( 832, 1216), "2:3"),
    ((1152,  896), "4:3"),
    (( 896, 1152), "3:4"),
    ((1536,  640), "21:9"),
]


def _best_aspect(w: int, h: int) -> str:
    r = w / max(h, 1)
    return min(_ASPECTS, key=lambda x: abs(x[0][0] / x[0][1] - r))[1]


def _poll_fal(request_id: str, queue_base: str, headers: dict, log: Callable) -> bytes:
    """轮询 fal.ai 队列直到完成，返回图片字节。"""
    status_url = f"{queue_base}/requests/{request_id}"
    result_url = f"{queue_base}/requests/{request_id}/response"
    for i in range(_MAX_POLLS):
        time.sleep(_POLL_SEC)
        try:
            st = _session.get(status_url, headers=headers, timeout=15)
        except Exception as e:
            log(f"  轮询错误: {e}"); continue
        if st.status_code != 200: continue
        status = st.json().get("status", "")
        log(f"  [{i+1}] {status}")
        if status == "COMPLETED":
            res = _session.get(result_url, headers=headers, timeout=20)
            if res.status_code != 200:
                raise ValueError(f"fal.ai 结果获取失败: {res.status_code}")
            images = res.json().get("images", [])
            if not images: raise ValueError("fal.ai 结果中无图片")
            img_url = images[0].get("url", "")
            if not img_url: raise ValueError("fal.ai 结果中无图片 URL")
            log("  下载图片中…")
            return _safe_get_image(img_url, timeout=120)
        if status in ("FAILED", "CANCELLED"):
            raise ValueError(f"fal.ai 任务失败: {status}")
    raise ValueError("fal.ai 等待超时（>120s），建议检查网络或换用其他接口")


def try_fal_flux(prompt: str, w: int, h: int, seed: int,
                 cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("fal_key", "").strip()
    if not key:
        raise ValueError("需要 fal.ai API Key！注册：https://fal.ai/")

    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    ref_image = cfg.get("_ref_image")        # bytes or None
    strength  = cfg.get("_ref_strength", 0.6)

    if ref_image is not None:
        # ── 图生图模式：flux-general/image-to-image ───────────────
        b64 = base64.b64encode(ref_image).decode()
        image_url = f"data:image/png;base64,{b64}"
        log(f"► fal.ai FLUX 图生图  强度={strength:.1f}")
        payload = {
            "prompt":     prompt,
            "image_url":  image_url,
            "strength":   float(strength),
            "image_size": {"width": w, "height": h},
            "seed":       seed % 2_147_483_647,
            "num_images": 1,
        }
        queue_base = _QUEUE_I2I
        label = "fal.ai/FLUX-img2img"
    else:
        # ── 文生图模式（原逻辑）──────────────────────────────────
        aspect = _best_aspect(w, h)
        log(f"► fal.ai FLUX Pro Ultra  宽高比={aspect}")
        payload = {
            "prompt":        prompt,
            "aspect_ratio":  aspect,
            "seed":          seed % 2_147_483_647,
            "output_format": "jpeg",
            "raw":           False,
        }
        queue_base = _QUEUE_T2I
        label = "fal.ai/FLUX-Ultra"

    # ── 提交到队列（持锁以控制提交频率）──────────────────────────
    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _session.post(queue_base, headers=headers, json=payload, timeout=30)
        except Exception as e:
            _LAST_DONE[0] = time.time()
            raise ValueError(f"无法连接 fal.ai: {e}")
        _LAST_DONE[0] = time.time()

    if resp.status_code == 401: raise ValueError("fal.ai API Key 无效")
    if resp.status_code == 429: raise ValueError("fal.ai 速率限制，请稍后再试")
    if resp.status_code != 200:
        raise ValueError(f"fal.ai 返回 {resp.status_code}: {_safe_error_text(resp)}")

    request_id = resp.json().get("request_id", "")
    if not request_id: raise ValueError("fal.ai 未返回 request_id")
    log(f"  已提交  ID={request_id[:14]}…  等待生成…")

    # ── 轮询（锁外执行，不阻塞其他线程提交）─────────────────────
    data = _poll_fal(request_id, queue_base, headers, log)
    log(f"  ✓ {label} 成功  {len(data) // 1024}KB")
    return data, label
