"""
services/providers/xai_grok.py  v2
────────────────────────────────────────────────────────────────
xAI Grok Imagine — Aurora 图像模型
  端点: POST https://api.x.ai/v1/images/generations
  认证: Bearer Token
  模型: grok-2-image-1212（OpenAI 兼容格式）
  响应: {data:[{url: "..."}]}

v2 修复（2026-03）：
  · 移除 "size" 参数 —— xAI 官方文档明确说明 grok-2-image-1212
    当前版本不支持调整尺寸、质量或风格（传入 size 会返回 HTTP 400）
  · 图片固定输出 1024×1024 JPEG，由 API 自动决定

额度说明（2026-03 现状）：
  · 新用户注册赠送 $25 免费额度（无需消费即可使用）
  · 消费满 $5 后可激活数据共享计划，额外获得 $150/月额度
  · 按量计费：$0.07/张
  · 充值/管理：https://console.x.ai
"""

import base64
import threading
import time
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, validate_image_url as _validate_image_url, safe_error_text as _safe_error_text


PROVIDER_INFO = {
    "name": "💎 xAI Grok Imagine",
    "category": "paid",
    "config_key": "xai_key",
}




# ── 串行锁 ────────────────────────────────────────────────────────────
_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 2.0

_ENDPOINT = "https://api.x.ai/v1/images/generations"
_MODEL    = "grok-2-image-1212"
_TIMEOUT  = 120
_MAX_RETRIES = 3


def try_xai_grok(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("xai_key", "").strip()
    if not key:
        raise ValueError(
            "需要 xAI API Key！\n"
            "注册地址：https://x.ai/api\n"
            "新用户赠送 $25 额度（约 350 张图），消费 $5 后可额外获得 $150/月"
        )

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }

    # ── 注意：grok-2-image-1212 当前不支持 size/quality/style 参数 ──
    # 传入 size 会返回 HTTP 400 "Argument not supported: size"
    # 图片固定生成 1024×1024 JPEG，API 自动决定尺寸
    payload = {
        "model":           _MODEL,
        "prompt":          prompt,
        "n":               1,
        "response_format": "url",
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)

        last_err = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                log(f"[xAI Grok] 尝试 {attempt}/{_MAX_RETRIES}（Aurora 模型，固定 1024×1024）…")
                resp = _session.post(
                    _ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=_TIMEOUT,
                )
                if resp.status_code == 429:
                    log("[xAI Grok] 速率限制（5 req/s），等待 30s…")
                    time.sleep(30)
                    continue
                if resp.status_code == 402:
                    raise ValueError(
                        "xAI 账户余额不足。\n"
                        "充值地址：https://console.x.ai\n"
                        "提示：消费满 $5 后可开启数据共享计划获得 $150/月免费额度"
                    )
                if resp.status_code == 401:
                    raise ValueError(
                        "xAI API Key 无效或已过期，请前往 https://console.x.ai 重新生成。"
                    )
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {_safe_error_text(resp)}"
                    )

                data = resp.json()
                image_bytes = _extract_image(data, log)
                _LAST_DONE[0] = time.time()
                log("[xAI Grok] 生成成功 ✓ (Aurora / 1024×1024 JPEG)")
                return (image_bytes, f"xAI/{_MODEL}")

            except (ValueError, RuntimeError) as e:
                last_err = e
                log(f"[xAI Grok] 错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(4 * attempt)
            except requests.RequestException as e:
                last_err = RuntimeError(str(e))
                log(f"[xAI Grok] 网络错误：{e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(4 * attempt)

        _LAST_DONE[0] = time.time()
        raise RuntimeError(f"xAI Grok 全部重试失败：{last_err}")


def _extract_image(data: dict, log: Callable) -> bytes:
    """解析 OpenAI 兼容的 {data:[{url}]} 或 {data:[{b64_json}]} 格式。"""
    items = data.get("data", [])
    if not items:
        raise ValueError(f"xAI 响应无 data 字段：{data}")

    url = items[0].get("url", "")
    if url:
        log(f"[xAI Grok] 下载图片：{url[:80]}…")
        if not _validate_image_url(url):
            raise RuntimeError(f"Blocked unsafe image URL: {url[:100]}")
        r = _session.get(url, timeout=60)
        r.raise_for_status()
        return r.content

    b64 = items[0].get("b64_json", "")
    if b64:
        return base64.b64decode(b64)

    raise ValueError(f"xAI 响应无 url 或 b64_json：{items[0]}")
