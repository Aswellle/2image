"""
services/providers/xai_grok.py  v4
────────────────────────────────────────────────────────────────
xAI Grok Imagine 图像模型
  端点: POST https://api.x.ai/v1/images/generations
  认证: Bearer Token
  模型: grok-imagine-image-2.0（官方推荐）/ grok-imagine-image
  响应: {data:[{url: "..."} | {b64_json: "..."}]}

v4 更新（2026-11，对照 docs.x.ai 官方模型页与生图指南核实）：
  · grok-imagine-image-quality 已不在官方模型表（仅存
    grok-imagine-image-2.0 与 grok-imagine-image），模型改由
    config.model_catalog 目录提供（cfg["xai_model"] 可切换）
  · 现已支持宽高比与分辨率控制：aspect_ratio 取最接近请求比例的
    枚举值，resolution 按 长边≤1024→1k、否则 2k 映射
  · quality 参数仅 2.0 支持，auto 档交由 API 自行决策，不显式传

v3 修复（2026-07）：
  · grok-2-image-1212 已于 2026-02-28 弃用，旧模型 id 请求直接失败
  · 图片返回 url（临时托管）或 b64_json

额度说明（以官方页面为准）：
  · 新用户注册赠送 $25 免费额度（无需消费即可使用）
  · 消费满 $5 后可激活数据共享计划，额外获得 $150/月额度
  · 按量计费：imagine-image $0.02/张、imagine-image-2.0 $0.04/张
  · 充值/管理：https://console.x.ai
"""

import base64
import threading
import time
from typing import Callable, Tuple

import requests

from config.model_catalog import XAI_IMAGE_DEFAULT, XAI_IMAGE_MODELS
from services.generation.errors import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderQuotaError,
    ProviderTransientError,
)
from services.providers._net import (
    get_session as _get_session,
)
from services.providers._net import (
    raise_for_response,
)
from services.providers._net import (
    safe_get_image as _safe_get_image,
)
from services.providers._net import (
    validate_image_url as _validate_image_url,
)

PROVIDER_INFO = {
    "id": "xai_grok",
    "name": "💎 xAI Grok Imagine",
    "category": "paid",
    "config_key": "xai_key",
}


# ── 串行锁 ────────────────────────────────────────────────────────────
_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 2.0

_ENDPOINT = "https://api.x.ai/v1/images/generations"
_TIMEOUT = 120
_MAX_RETRIES = 3

# 官方生图指南给出的 aspect_ratio 枚举（2026-11）
_ASPECT_RATIOS = [
    (1, 1),
    (16, 9),
    (9, 16),
    (4, 3),
    (3, 4),
    (3, 2),
    (2, 3),
    (2, 1),
    (1, 2),
    (21, 9),
    (9, 21),
    (19, 10),
    (10, 19),
    (20, 9),
    (9, 20),
]


def _aspect_ratio(w: int, h: int) -> str:
    """取与请求宽高比最接近的官方枚举值。"""
    r = w / max(h, 1)
    rw, rh = min(_ASPECT_RATIOS, key=lambda s: abs(s[0] / s[1] - r))
    return f"{rw}:{rh}"


def try_xai_grok(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("xai_key", "").strip()
    if not key:
        raise ProviderConfigError(
            "需要 xAI API Key！\n"
            "注册地址：https://x.ai/api\n"
            "新用户赠送 $25 额度（约 350 张图），消费 $5 后可额外获得 $150/月"
        )

    # 模型目录接线：存量配置值不在目录时归一化到默认（旧 -quality ID 已在册移除）
    model = cfg.get("xai_model", "").strip()
    if model not in XAI_IMAGE_MODELS:
        model = XAI_IMAGE_DEFAULT

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    # 官方参数（docs.x.ai 生图指南）：aspect_ratio（15 档枚举）、
    # resolution（1k/2k）、quality（仅 2.0，auto 即默认，不显式传）
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "aspect_ratio": _aspect_ratio(w, h),
        "resolution": "1k" if max(w, h) <= 1024 else "2k",
        "response_format": "url",
    }
    if seed and seed > 0:
        payload["seed"] = seed % 2147483647

    # ── 持锁范围仅限限速等待：预占时间槽后立即放锁 ──────────────────
    # 修复：原版锁覆盖整个重试循环，429 退避与 HTTP 超时都持锁，
    # 批量并发时其余线程最长被阻塞数分钟。等待/请求均在锁外执行。
    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        _LAST_DONE[0] = time.time()  # 预占时间槽，锁外等待/请求

    last_err = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            log(
                f"[xAI Grok] 尝试 {attempt}/{_MAX_RETRIES}  模型={model}"
                f"  比例={payload['aspect_ratio']}  {payload['resolution']}…"
            )
            resp = _get_session().post(
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
                raise ProviderQuotaError(
                    "xAI 账户余额不足。\n"
                    "充值地址：https://console.x.ai\n"
                    "提示：消费满 $5 后可开启数据共享计划获得 $150/月免费额度"
                )
            if resp.status_code == 401:
                raise ProviderAuthError("xAI API Key 无效或已过期，请前往 https://console.x.ai 重新生成。")
            if resp.status_code != 200:
                raise_for_response(resp, "💎 xAI Grok Imagine")

            data = resp.json()
            image_bytes = _extract_image(data, log)
            log("[xAI Grok] 生成成功 ✓")
            return (image_bytes, f"xAI/{model}")

        except ProviderError:
            raise  # 类型化错误直通：重试/回退由 orchestrator 按 code 决策
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

    raise ProviderTransientError(f"xAI Grok 全部重试失败：{last_err}")


def _extract_image(data: dict, log: Callable) -> bytes:
    """解析 OpenAI 兼容的 {data:[{url}]} 或 {data:[{b64_json}]} 格式。"""
    items = data.get("data", [])
    if not items:
        raise ProviderInvalidResponseError(f"xAI 响应无 data 字段：{data}")

    url = items[0].get("url", "")
    if url:
        _validate_image_url(url)
        log(f"[xAI Grok] 下载图片：{url[:80]}…")
        return _safe_get_image(url, timeout=60)

    b64 = items[0].get("b64_json", "")
    if b64:
        return base64.b64decode(b64)

    raise ProviderInvalidResponseError(f"xAI 响应无 url 或 b64_json：{items[0]}")
