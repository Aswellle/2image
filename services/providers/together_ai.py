"""
services/providers/together_ai.py
Together AI — FLUX.1-schnell
端点: POST https://api.together.xyz/v1/images/generations
认证: Bearer Token
响应: {data:[{url: "..."}]}

FIX 2026-07: 官方模型页明确写着 "FLUX.1 [schnell] Free" 已不再挂在
Together 的 Serverless API 上（"This model is not available on
Together's Serverless API"）——旧的 "...-Free" 模型 id 大概率直接
404。改回不带 -Free 后缀的普通 black-forest-labs/FLUX.1-schnell，
但该模型当前是否仍对无付费账户免费尚未最终确认；若持续失败，
调度器会按现有逻辑自动跳到下一个接口，不影响整体生成流程。
"""
import threading
import time
import requests
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, validate_image_url as _validate_image_url, safe_error_text as _safe_error_text, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "id": "together_ai",
    "name": "Together AI (FLUX Free·免费)",
    "category": "free",
    "config_key": "together_key",
}


# ── 串行锁（防批量变体并发触发速率限制）──────────────────────────────
_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0   # Together AI 建议最小请求间隔（秒）

_ENDPOINT  = "https://api.together.xyz/v1/images/generations"
_MODEL     = "black-forest-labs/FLUX.1-schnell"
_TIMEOUT   = 120
_MAX_RETRIES = 3


def try_together_ai(
    prompt: str, w: int, h: int, seed: int,
    cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("together_key", "").strip()
    if not key:
        raise ValueError(
            "需要 Together AI API Key！注册：https://api.together.ai/"
        )

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model":  _MODEL,
        "prompt": prompt,
        "n":      1,
        "width":  _clamp(w),
        "height": _clamp(h),
    }
    if seed and seed > 0:
        payload["seed"] = seed

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[Together AI] 尝试 {attempt}/{_MAX_RETRIES}…")
                resp = _session.post(
                    _ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=_TIMEOUT,
                )
                if resp.status_code == 429:
                    log("[Together AI] 触发速率限制，等待 30s…")
                    time.sleep(30)
                    continue
                if resp.status_code == 402:
                    raise ValueError("Together AI 余额不足，请前往 https://api.together.ai/ 充值。")
                if resp.status_code == 404:
                    raise ValueError(
                        "Together AI 模型不可用（FLUX.1-schnell 可能已从免费 "
                        "Serverless API 下线），请前往 https://api.together.ai/ 确认当前可用模型。"
                    )
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {_safe_error_text(resp)}"
                    )

                data = resp.json()
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log("[Together AI] 生成成功 ✓")
                return (image_bytes, "TogetherAI/FLUX.1-schnell")

            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[Together AI] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                log(f"[Together AI] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(3 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"Together AI 全部重试失败：{last_err}")


def _extract_image(data: dict, log: Callable) -> bytes:
    """解析 {data:[{url}]} 格式并下载图片。"""
    items = data.get("data", [])
    if not items:
        raise ValueError(f"Together AI 响应无 data 字段：{data}")

    url = items[0].get("url", "")
    if not url:
        import base64
        b64 = items[0].get("b64_json", "")
        if b64:
            return base64.b64decode(b64)
        raise ValueError(f"Together AI 响应无 url 或 b64_json：{items[0]}")

    log(f"[Together AI] 下载图片：{url[:80]}…")
    return _safe_get_image(url, timeout=60)


# Together AI FLUX Free 端点支持的尺寸：必须是 64 的倍数，范围 256~1440
def _clamp(px: int) -> int:
    """将像素值对齐到最近的 64 倍数，并限制在 [256, 1440] 范围内。"""
    px = max(256, min(1440, px))
    return round(px / 64) * 64
