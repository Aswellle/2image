"""
services/providers/gemini_nano_banana_pro.py
Google Gemini 3 Pro Image ("Nano Banana Pro") — 旗舰级图像模型
端点: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent
认证: Header x-goog-api-key（与 gemini.py 共用同一个 Google AI Studio Key）
响应: candidates[0].content.parts[].inlineData.data  (base64)

与 gemini.py（Nano Banana / gemini-2.5-flash-image）的区别：
  · 画质更高、支持原生 1K 输出并可放大到 2K/4K，推理式生成
  · 官方定价无免费额度（付费按量计费），因此归类为 paid
  · 复用同一个 gemini_key，只是调用更贵的模型，无需单独申请 Key
"""

import base64
import threading
import time
import requests
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text


PROVIDER_INFO = {
    "id": "gemini_nano_banana_pro",
    "name": "💎 Nano Banana Pro (Gemini 3 Pro Image)",
    "category": "paid",
    "config_key": "gemini_key",
    "supports_img2img": True,
}


_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 2.0

_MODEL = "gemini-3-pro-image"
_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{_MODEL}:generateContent"
)
_TIMEOUT = 120
_MAX_RETRIES = 3


def _guess_mime(image_bytes: bytes) -> str:
    """按文件魔数猜测参考图 MIME 类型，供 inline_data.mimeType 使用。"""
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def try_gemini_nano_banana_pro(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("gemini_key", "").strip()
    if not key:
        raise ValueError("需要 Google Gemini API Key！注册：https://aistudio.google.com/")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    }

    ref_image = cfg.get("_ref_image")   # bytes or None（图生图参考图）
    parts = [{"text": prompt}]
    if ref_image is not None:
        parts.append({
            "inline_data": {
                "mime_type": _guess_mime(ref_image),
                "data": base64.b64encode(ref_image).decode("ascii"),
            }
        })
        log(f"[Nano Banana Pro] 图生图模式，参考图 {len(ref_image)//1024}KB")

    payload = {
        "contents": [{"parts": parts}],
        # responseModalities 必须同时包含 TEXT 和 IMAGE，纯 IMAGE 会被拒绝
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Nano Banana Pro] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = _session.post(
                    _ENDPOINT, headers=headers, json=payload, timeout=_TIMEOUT,
                )
                if resp.status_code == 429:
                    log("[Nano Banana Pro] 触发速率限制，等待 30s…")
                    time.sleep(30)
                    continue
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {_safe_error_text(resp)}"
                    )

                data = resp.json()
                image_bytes = _extract_image(data)
                _LAST_DONE[0] = time.time()
                log("[Nano Banana Pro] 生成成功 ✓")
                return (image_bytes, "Gemini/Nano-Banana-Pro")

            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[Nano Banana Pro] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                log(f"[Nano Banana Pro] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Nano Banana Pro 全部重试失败：{last_err}")


def _extract_image(data: dict) -> bytes:
    """从 Gemini 响应中提取 base64 图片数据并解码。"""
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Nano Banana Pro 响应无 candidates（格式异常）")

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        inline = part.get("inlineData", {})
        b64 = inline.get("data", "")
        if b64:
            try:
                return base64.b64decode(b64)
            except Exception as e:
                raise ValueError(f"base64 解码失败：{e}")

    raise ValueError("Nano Banana Pro 响应中未找到图片数据")
