"""
services/providers/gemini.py — Google Gemini 图像生成（文生图 + 图生图）

支持 Nano Banana 系列模型：
  · gemini-2.5-flash-image      → Nano Banana v1（即将下线，2026-10）
  · gemini-3.1-flash-image      → Nano Banana 2（当前稳定版，默认）
  · gemini-3.1-flash-lite-image → Nano Banana 2 Lite（轻量快速）
  · gemini-3-pro-image          → Nano Banana Pro（最强画质）

端点：POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
认证：Header x-goog-api-key
响应：candidates[0].content.parts[].inlineData.data（base64）
"""
import base64
import threading
import time
from typing import Callable, Tuple

from config.model_catalog import (
    GEMINI_IMAGE_MODELS,
    GEMINI_IMAGE_DEFAULT,
    GEMINI_IMAGE_NAMES,
    GEMINI_IMAGE_DEPRECATED,
)
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text


PROVIDER_INFO = {
    "id": "gemini",
    "name": "Google Gemini Nano Banana (免费额度)",
    "category": "free",
    "config_key": "gemini_key",
    "description": "Nano Banana 系列：v1/v2/v2 Lite/Pro",
}









# ── 串行锁（防批量变体并发触发速率限制）──────────────────────────────
_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 2.0  # Gemini 免费层建议间隔

_DEFAULT_MODEL = GEMINI_IMAGE_DEFAULT  # 默认使用 Nano Banana 2
_ENDPOINT_TPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
_TIMEOUT = 90
_MAX_RETRIES = 3



# ── 串行锁（防批量变体并发触发速率限制）──────────────────────────────
_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 2.0  # Gemini 免费层建议间隔

_DEFAULT_MODEL = GEMINI_IMAGE_DEFAULT  # 默认图像模型（可选值见 config.model_catalog）
_ENDPOINT_TPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
_TIMEOUT = 90
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


def try_gemini(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("gemini_key", "").strip()
    if not key:
        raise ValueError("需要 Google Gemini API Key！注册：https://aistudio.google.com/")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    }

    # 可通过 cfg["gemini_model"] 切换图像模型（默认 gemini-2.5-flash-image，
    # 也可选 gemini-3.1-flash-image 等最新 GA 模型）
    model    = cfg.get("gemini_model", _DEFAULT_MODEL)
    endpoint = _ENDPOINT_TPL.format(model=model)

    ref_image = cfg.get("_ref_image")   # bytes or None（图生图参考图）
    parts = [{"text": prompt}]
    if ref_image is not None:
        parts.append({
            "inline_data": {
                "mime_type": _guess_mime(ref_image),
                "data": base64.b64encode(ref_image).decode("ascii"),
            }
        })
        log(f"[Gemini] 图生图模式，参考图 {len(ref_image)//1024}KB")

    # Gemini generateContent 图像生成请求体
    # 注意：responseModalities 必须同时包含 TEXT 和 IMAGE，
    # 只传 IMAGE 会被官方 API 拒绝（哪怕文本部分被忽略不用）。
    payload = {
        "contents": [
            {
                "parts": parts
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Gemini] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = _session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=_TIMEOUT,
                )
                if resp.status_code == 429:
                    log("[Gemini] 触发速率限制，等待 30s…")
                    time.sleep(30)
                    continue
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {_safe_error_text(resp)}"
                    )

                data = resp.json()
                # 解析 base64 图片数据
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log("[Gemini] 生成成功 ✓")
                return (image_bytes, f"Gemini/{model}")

            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[Gemini] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                log(f"[Gemini] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Gemini 全部重试失败：{last_err}")


def _extract_image(data: dict, log: Callable) -> bytes:
    """从 Gemini 响应中提取 base64 图片数据并解码。"""
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini 响应无 candidates（格式异常）")

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        inline = part.get("inlineData", {})
        b64 = inline.get("data", "")
        if b64:
            try:
                return base64.b64decode(b64)
            except Exception as e:
                raise ValueError(f"base64 解码失败：{e}")

    raise ValueError("Gemini 响应中未找到图片数据")
