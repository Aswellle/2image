"""
services/providers/pollinations.py
Pollinations.AI — 完全免费，支持 img2img
端点: https://image.pollinations.ai/
参数: prompt, width, height, seed, image (URL, base64)
响应: 图片直接返回
"""
import base64, io, threading, time
from typing import Callable, Tuple
import requests
from PIL import Image

_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 1.5
_TIMEOUT  = 120
_MAX_RETRIES = 3


def try_pollinations(
    prompt: str, w: int, h: int, seed: int,
    cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    """文生图：直接拼接 URL，下载返回图片。"""
    params = {
        "prompt": prompt[:1500],
        "width": min(max(w, 256), 1536),
        "height": min(max(h, 256), 1536),
        "seed": seed if seed and seed > 0 else None,
        "model": "default",
    }
    params = {k: v for k, v in params.items() if v is not None}
    url = "https://image.pollinations.ai/?" + "&".join(
        f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()
    )

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Pollinations] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = requests.get(url, timeout=_TIMEOUT,
                                     headers={"User-Agent": "2image-app/1.0"})
                if resp.status_code == 403:
                    raise RuntimeError("Pollinations 访问被拒绝（可能 IP 被限制）")
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                if not resp.content or len(resp.content) < 1024:
                    raise RuntimeError("返回内容过小，可能非图片")

                _LAST_DONE[0] = time.time()
                log("[Pollinations] 生成成功 ✓")
                return (resp.content, "Pollinations.AI")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Pollinations] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(2 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e)); log(f"[Pollinations] 网络错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(2 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Pollinations 全部重试失败：{last_err}")


def try_pollinations_img2img(
    prompt: str, w: int, h: int, seed: int,
    source_bytes: bytes, cfg: dict, log: Callable,
    strength: float = None,
) -> Tuple[bytes, str]:
    """
    图生图：将 source_bytes 作为参考图，
    Pollinations 通过 URL 参数 image=<url> 或 base64 编码实现。
    这里用 base64 data URI 传给 image 参数。
    """
    b64 = base64.b64encode(source_bytes).decode()
    image_ref = f"data:image/jpeg;base64,{b64}"

    params = {
        "prompt": prompt[:1500],
        "width": min(max(w, 256), 1536),
        "height": min(max(h, 256), 1536),
        "seed": seed if seed and seed > 0 else None,
        "image": image_ref,
        "model": "default",
    }
    params = {k: v for k, v in params.items() if v is not None}
    # image 参数较长，放到最后
    img_param = params.pop("image")

    url = "https://image.pollinations.ai/?" + "&".join(
        f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()
    ) + f"&image={requests.utils.quote(img_param)}"

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Pollinations img2img] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = requests.get(url, timeout=_TIMEOUT,
                                     headers={"User-Agent": "2image-app/1.0"})
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                _LAST_DONE[0] = time.time()
                log("[Pollinations img2img] 生成成功 ✓")
                return (resp.content, "Pollinations.AI/img2img")
            except (ValueError, RuntimeError) as e:
                last_err = e; log(f"[Pollinations img2img] 错误：{e}")
                if attempt < _MAX_RETRIES: time.sleep(2 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                if attempt < _MAX_RETRIES: time.sleep(2 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Pollinations img2img 全部重试失败：{last_err}")
