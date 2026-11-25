"""
services/providers/minimax_image.py — MiniMax 图像生成（文生图 + 参考图编辑）

支持模型（2026-11-22 换代）：
  · MiniMax-H3-Image           — H3 旗舰（默认；文生图+编辑，最高 20MP）
  · MiniMax-H3-Image-Highspeed — 同参数更快变体

端点（2026-11-26 对照 platform.minimax.io 官方 API 参考接入）：
  · 文生图: POST https://api.minimax.io/v1/images/generations
            model / prompt / aspect_ratio+area / n / response_format
  · 编辑:   POST https://api.minimax.io/v1/images/edits
            model / prompt / images[{image_url}] / size=auto / aspect_ratio+area
            （1–16 张参考图；image_url 接受公网 URL、mm_file:// 与
             data:image/<fmt>;base64,<...> data URI，本机参考图走 data URI）
认证: Header Authorization: Bearer <key>
响应: data[].url（或 b64_json），单项失败在 data[].error，usage.generated_images 计成功数

图生图注意：官方声明编辑端点「非幂等」——超时/断连后服务端仍会完成并计费，
因此编辑路径不做内联重试，瞬态错误标记为不可重试，避免重复扣费。
"""

import base64
import io
import threading
import time
from typing import Callable, Tuple

import requests

from config.model_catalog import (
    MINIMAX_IMAGE_DEFAULT,
    MINIMAX_IMAGE_MODELS,
    MINIMAX_IMAGE_NAMES,
)
from services.generation.errors import (
    ProviderConfigError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderTransientError,
)
from services.providers._net import (
    get_session as _get_session,
    raise_for_response,
    safe_get_image as _safe_get_image,
)


PROVIDER_INFO = {
    "id": "minimax_image",
    "name": "MiniMax Image (付费)",
    "category": "commercial",
    "config_key": "minimax_key",
    "description": "MiniMax H3-Image 文生图 + 参考图编辑（最高 20MP）",
    "supports_img2img": True,
}


_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 2.0

_ENDPOINT = "https://api.minimax.io/v1/images/generations"
_EDIT_ENDPOINT = "https://api.minimax.io/v1/images/edits"
_TIMEOUT = 120
# 官方：编辑端点服务端最长等待 600s，客户端超时不得短于该值
_EDIT_TIMEOUT = 600
_MAX_RETRIES = 3
# 参考图原始字节上限（请求体 64MiB，base64 膨胀约 4/3，留出 prompt 余量）
_MAX_REF_BYTES = 45 * 1024 * 1024

# (ratio_value, aspect_ratio 枚举)
_ASPECTS = [
    (1 / 3, "1:3"),
    (3, "3:1"),
    (9 / 16, "9:16"),
    (16 / 9, "16:9"),
    (2 / 3, "2:3"),
    (3 / 2, "3:2"),
    (3 / 4, "3:4"),
    (4 / 3, "4:3"),
    (1, "1:1"),
]


def _best_aspect(w: int, h: int) -> str:
    r = w / max(h, 1)
    return min(_ASPECTS, key=lambda x: abs(x[0] - r))[1]


def _best_area(w: int, h: int) -> str:
    """按请求像素量选 area 档（H3 面积允许 [655360, 20000000] px）。"""
    pixels = max(w, 1) * max(h, 1)
    if pixels <= 1_100_000:
        return "1K"
    if pixels <= 4_500_000:
        return "2K"
    return "4K"


def _wait_turn() -> None:
    """限速预占：持锁范围仅限等待，避免批量并发时锁住整个请求周期。"""
    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        _LAST_DONE[0] = time.time()  # 预占时间槽，锁外等待/请求


def try_minimax_image(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("minimax_key", "").strip()
    if not key:
        raise ProviderConfigError("需要 MiniMax API Key，请在「💎 付费接口配置」中填写")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    model = cfg.get("minimax_model", "").strip()
    if model not in MINIMAX_IMAGE_MODELS:
        if model:
            log(f"[MiniMax] 模型 {model!r} 不在目录，已归一化到默认 {MINIMAX_IMAGE_DEFAULT}")
        model = MINIMAX_IMAGE_DEFAULT

    ref_image = cfg.get("_ref_image")  # bytes or None
    if ref_image is not None:
        return _edit_image(prompt, w, h, ref_image, model, headers, log)

    aspect = _best_aspect(w, h)
    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect,
        "area": _best_area(w, h),
        "n": 1,
        "response_format": "url",
    }
    log(f"► MiniMax {MINIMAX_IMAGE_NAMES.get(model, model)}  文生图  宽高比={aspect}  档={payload['area']}")

    # ── 持锁范围仅限限速等待：预占时间槽后立即放锁 ──────────────────
    # 修复：原版锁覆盖整个重试循环，429 退避与 HTTP 超时都持锁，
    # 批量并发时其余线程最长被阻塞数分钟。等待/请求均在锁外执行。
    _wait_turn()

    last_err = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            log(f"[MiniMax] 尝试 {attempt}/{_MAX_RETRIES}…")
            resp = _get_session().post(
                _ENDPOINT,
                headers=headers,
                json=payload,
                timeout=_TIMEOUT,
            )
            if resp.status_code == 429:
                log("[MiniMax] 速率限制，等待 20s…")
                time.sleep(20)
                continue
            if resp.status_code != 200:
                raise_for_response(resp, "MiniMax Image")

            data = resp.json()
            image_bytes = _extract_image(data)
            log("[MiniMax] 生成成功 ✓")
            return (image_bytes, f"MiniMax/{MINIMAX_IMAGE_NAMES.get(model, model)}")

        except ProviderError:
            raise  # 类型化错误直通：重试/回退由 orchestrator 按 code 决策
        except (ValueError, RuntimeError) as e:
            last_err = e
            log(f"[MiniMax] 错误：{e}")
            if attempt < _MAX_RETRIES:
                time.sleep(3 * attempt)
        except requests.RequestException as e:
            last_err = RuntimeError(str(e))
            log(f"[MiniMax] 网络错误：{e}")
            if attempt < _MAX_RETRIES:
                time.sleep(3 * attempt)

    raise ProviderTransientError(f"MiniMax 全部重试失败：{last_err}")


def _edit_image(
    prompt: str,
    w: int,
    h: int,
    ref_image: bytes,
    model: str,
    headers: dict,
    log: Callable,
) -> Tuple[bytes, str]:
    """H3 参考图编辑：单次提交，失败不内联重试（端点非幂等，重试会重复计费）。"""
    aspect = _best_aspect(w, h)
    area = _best_area(w, h)
    image_url = _ref_data_uri(ref_image)
    payload = {
        "model": model,
        "prompt": prompt,
        # 官方 schema：size=auto 时才能同时使用 aspect_ratio + area
        "images": [{"image_url": image_url}],
        "n": 1,
        "size": "auto",
        "aspect_ratio": aspect,
        "area": area,
        "response_format": "url",
        # 输出用 jpeg（官方默认）：20MP 的 PNG 可能超过下载 25MB 上限，
        # 本机保存时统一再转码为 PNG，不受影响
        "output_format": "jpeg",
    }
    name = MINIMAX_IMAGE_NAMES.get(model, model)
    log(f"► MiniMax {name}  图生图（参考图编辑）  宽高比={aspect}  档={area}  参考图={len(ref_image) // 1024}KB")

    _wait_turn()
    try:
        resp = _get_session().post(_EDIT_ENDPOINT, headers=headers, json=payload, timeout=_EDIT_TIMEOUT)
    except requests.RequestException as exc:
        raise _no_retry(ProviderTransientError(f"MiniMax 编辑请求未完成：{exc}"))

    if resp.status_code != 200:
        try:
            raise_for_response(resp, "MiniMax Image")
        except ProviderTransientError as exc:
            # 5xx / 超时可能已在服务端生成并计费：禁止 orchestrator 重试
            raise _no_retry(exc)

    try:
        data = resp.json()
    except ValueError as exc:
        raise ProviderInvalidResponseError(f"MiniMax 编辑响应不是 JSON：{exc}")

    image_bytes = _extract_image(data)
    revised = ""
    items = data.get("data") or [{}]
    if isinstance(items[0], dict):
        revised = str(items[0].get("revised_prompt") or "")
    if revised:
        log(f"[MiniMax] 已按编辑提示词重写：{revised[:80]}…")
    log("[MiniMax] 图生图成功 ✓")
    return (image_bytes, f"MiniMax/{name}-edit")


def _no_retry(err: ProviderError) -> ProviderError:
    """实例级关闭重试：非幂等端点重复提交会产生重复扣费。"""
    err.retryable = False
    return err


# 官方允许 jpg/jpeg/png/webp/heic/heif；本机参考图可直传前三类的 data URI，
# 其余格式（如 BMP/GIF/TIFF）经 Pillow 转码为 PNG。
_MAGIC_IMAGE_TYPES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)


def _ref_data_uri(ref_image: bytes) -> str:
    """把本地参考图字节编码为 edits 端点接受的 data URI。"""
    mime = ""
    for magic, kind in _MAGIC_IMAGE_TYPES:
        if ref_image.startswith(magic):
            mime = kind
            break
    if not mime and ref_image[:4] == b"RIFF" and ref_image[8:12] == b"WEBP":
        mime = "image/webp"

    payload = ref_image
    if not mime:
        try:
            from PIL import Image

            with Image.open(io.BytesIO(ref_image)) as img:
                img.load()
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                payload = buf.getvalue()
            mime = "image/png"
        except Exception as exc:
            raise ProviderConfigError(f"MiniMax 图生图仅支持 PNG / JPEG / WEBP 参考图，且该文件转码失败：{exc}")

    if len(payload) > _MAX_REF_BYTES:
        raise ProviderConfigError(
            f"参考图过大（{len(payload) // (1024 * 1024)}MB），MiniMax 编辑请求体上限 64MB，请压缩后再试"
        )
    return f"data:{mime};base64,{base64.b64encode(payload).decode()}"


def _extract_image(data: dict) -> bytes:
    """响应体：{"data": [{"url": ...} | {"error": {...}}], "usage": {...}}。

    HTTP 200 仅代表至少一张成功；单项失败在 error 对象里。
    """
    items = data.get("data", [])
    if not items:
        raise ProviderInvalidResponseError(f"MiniMax 响应中无 data 数组：{data}")
    first = items[0]
    if not isinstance(first, dict):
        raise ProviderInvalidResponseError(f"MiniMax 响应 data 项类型异常：{first!r}")
    err = first.get("error")
    if err:
        raise ProviderInvalidResponseError(f"MiniMax 图片生成失败：{err.get('message', err)}")
    url = first.get("url", "")
    b64 = first.get("b64_json", "")
    if b64:
        return base64.b64decode(b64)
    if not url:
        raise ProviderInvalidResponseError(f"MiniMax 响应中既无 url 也无 b64_json：{first}")
    return _safe_get_image(url)
