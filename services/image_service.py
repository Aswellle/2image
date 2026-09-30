"""
services/image_service.py — 图片生成调度器 + 本地落盘

Phase 2 重构：
  - generate_image() 内部使用 GenerationOrchestrator（支持 cancellation/deadline/health/retry）
  - Provider 错误在边界映射到 ProviderError taxonomy
  - save_image_file() 改用 UUID 文件名 + 原子写入
  - 下载使用 bounded_download()
"""
import io
import os
import random
import tempfile
import uuid
from datetime import datetime
from typing import Callable

import requests
from PIL import Image, PngImagePlugin

from config.settings import IMAGES_DIR

from services.generation.cancellation import CancellationToken
from services.generation.errors import (
    DeadlineExceeded,
    GenerationCancelled,
    ProviderAuthError,
    ProviderError,
    ProviderPolicyError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderTransientError,
    classify_http_error,
)
from services.generation.orchestrator import GenerationOrchestrator
from services.logger import log_to_file
from services.providers import ALL_PROVIDERS, DEFAULT_ORDER
from services.providers._net import safe_error_text


def _wrap_provider_fn(fn: Callable) -> Callable:
    """Map provider exceptions to ProviderError taxonomy.

    Existing providers raise ValueError/RuntimeError with human-readable
    messages; the orchestrator needs ProviderError to make correct
    fallback decisions (e.g. 401 → don't retry, 400 → don't fallback).

    Classification order:
      1. Already a domain error → pass through untouched
      2. requests.HTTPError     → classify_http_error(status_code)
      3. requests.Timeout / ConnectionError → transient
      4. Message keyword match  → auth / quota / rate-limit / policy
      5. Anything else          → transient (retry, then fallback)
    """
    def wrapped(prompt, width, height, seed, cfg, log_cb):
        try:
            return fn(prompt, width, height, seed, cfg, log_cb)
        except (ProviderError, GenerationCancelled):
            raise  # Already domain errors, don't re-wrap
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None) or 0
            raise classify_http_error(status, safe_error_text(exc.response)
                                      if exc.response is not None else "") from exc
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise ProviderTransientError(f"{type(exc).__name__}: {exc}") from exc
        except Exception as exc:
            raise _classify_by_message(str(exc)) from exc
    wrapped.__name__ = getattr(fn, "__name__", "wrapped_provider")
    return wrapped


_AUTH_KEYWORDS = ("key", "token", "令牌", "密钥", "需要配置", "未配置", "无效",
                  "invalid", "missing", "required", "unauthorized", "401", "403")
_QUOTA_KEYWORDS = ("quota", "balance", "余额", "额度", "充值", "402", "insufficient")
_RATE_LIMIT_KEYWORDS = ("rate", "429", "限流", "too many", "频繁", "throttl")
_POLICY_KEYWORDS = ("policy", "nsfw", "safety", "content moderation",
                    "违规", "敏感", "审核", "不合规", "blocked")


def _classify_by_message(msg: str) -> ProviderError:
    """Best-effort classification of a provider's plain-text error."""
    lowered = msg.lower()
    if any(kw in lowered for kw in _QUOTA_KEYWORDS):
        return ProviderQuotaError(msg)
    if any(kw in lowered for kw in _RATE_LIMIT_KEYWORDS):
        return ProviderRateLimitError(msg)
    if any(kw in lowered for kw in _AUTH_KEYWORDS):
        return ProviderAuthError(msg)
    if any(kw in lowered for kw in _POLICY_KEYWORDS):
        return ProviderPolicyError(msg)
    return ProviderTransientError(msg)


def generate_image(prompt, w, h, seed, cfg,
                   provider_order=None, status_cb=None, log_cb=None,
                   ref_image: bytes | None = None,
                   strength: float = 0.6,
                   token: CancellationToken | None = None,
                   deadline_seconds: float = 180.0):
    """生成图片。

    ref_image: 参考图字节（图生图模式），None = 纯文生图。
    strength:  变化强度 0.1~0.9，越小越接近原图（仅 img2img 模式有效）。
    token:     可选的 CancellationToken，用于立即取消正在进行的生成。
    deadline_seconds: 任务级绝对截止时间（秒）。

    img2img 参数通过临时 cfg 副本传递给支持该功能的 provider，
    不影响原始 cfg（不会写入 config.json）。
    """
    if seed is None:
        seed = random.randint(0, 2_147_483_647)
    if log_cb is None:
        log_cb = log_to_file

    # 图生图：构造含临时参数的 cfg 副本，不污染原始配置
    eff_cfg = cfg
    if ref_image is not None:
        eff_cfg = {**cfg, "_ref_image": ref_image, "_ref_strength": float(strength)}
        log_to_file(f"[img2img] 参考图 {len(ref_image)//1024}KB  强度={strength:.1f}")

    order = list(provider_order or DEFAULT_ORDER)

    # Build providers dict with error mapping wrapper
    providers = {}
    for name in order:
        fn = ALL_PROVIDERS.get(name)
        if fn is not None:
            providers[name] = _wrap_provider_fn(fn)
    # Add any remaining providers not in explicit order as final fallback
    for name, fn in ALL_PROVIDERS.items():
        if name not in providers and fn is not None:
            providers[name] = _wrap_provider_fn(fn)

    orch = GenerationOrchestrator(
        providers=providers,
        deadline_seconds=deadline_seconds,
    )

    try:
        result = orch.run(
            prompt, w, h, seed, eff_cfg,
            log_cb=log_cb, status_cb=status_cb,
            token=token, provider_order=order,
        )
    except GenerationCancelled:
        raise  # Propagate to caller for special handling

    if result.cancelled:
        raise GenerationCancelled("生成已取消")
    if result.deadline_exceeded:
        raise DeadlineExceeded(f"生成超时（{deadline_seconds}s）")
    if result.image_bytes is not None:
        used = result.provider_id or ""
        # PAY-001: 记录付费估算消耗（免费接口为 no-op），单图/队列/批量统一入口
        try:
            from services.generation import budget
            total = budget.record_spend(used, cfg)
            if total and budget.is_paid(used):
                limit = budget.daily_budget(cfg)
                if limit > 0:
                    log_to_file(f"💰 付费消耗估算 +${budget.estimate_cost(used):.2f} "
                                f"（今日 ${total:.2f} / ${limit:.2f}）")
        except Exception:
            pass  # 预算记录失败绝不影响生成结果
        return result.image_bytes, used

    raise RuntimeError("所有接口均失败:\n" + "\n".join(result.errors))


def save_image_file(image_bytes, prompt,
                    seed: int = 0, provider: str = "",
                    translated: str = "", size: str = "") -> str:
    """
    Save image with UUID-based filename and atomic write.

    Filename format: YYYY/MM/DD/<uuid>.png
    Prevents collisions and path traversal.
    """
    date_dir = os.path.join(IMAGES_DIR, datetime.now().strftime("%Y/%m/%d"))
    os.makedirs(date_dir, exist_ok=True)

    file_id = uuid.uuid4().hex
    final_path = os.path.join(date_dir, f"{file_id}.png")

    img = Image.open(io.BytesIO(image_bytes))

    # Embed metadata in PNG tEXt chunks
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Prompt", prompt[:500])
    if translated:
        meta.add_text("Translated", translated[:500])
    if seed:
        meta.add_text("Seed", str(seed))
    if provider:
        meta.add_text("Provider", provider)
    if size:
        meta.add_text("Size", size)

    # Atomic write: write to temp file, then rename
    fd, tmp_path = tempfile.mkstemp(dir=date_dir, suffix=".tmp")
    try:
        os.close(fd)
        img.save(tmp_path, "PNG", pnginfo=meta)
        os.replace(tmp_path, final_path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return final_path
