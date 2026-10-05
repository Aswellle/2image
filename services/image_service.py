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
import re
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


# 拉丁关键词用词边界正则匹配，避免子串误命中（如 "rate" 命中 "generate"）；
# 中文关键词无词边界概念，保留子串匹配。
_AUTH_LATIN = (r"\bkey\b", r"\btoken\b", r"\binvalid\b", r"\bmissing\b",
               r"\brequired\b", r"\bunauthorized\b", r"\b40[13]\b")
_AUTH_CJK = ("令牌", "密钥", "需要配置", "未配置", "无效")
_QUOTA_LATIN = (r"\bquota\b", r"\bbalance\b", r"\binsufficient\b", r"\b402\b")
_QUOTA_CJK = ("余额", "额度", "充值")
_RATE_LIMIT_LATIN = (r"\brate limit\b", r"\b429\b", r"\btoo many\b", r"\bthrottl")
_RATE_LIMIT_CJK = ("限流", "频繁")
_POLICY_LATIN = (r"\bpolicy\b", r"\bnsfw\b", r"\bsafety\b",
                 r"\bcontent moderation\b", r"\bblocked\b")
_POLICY_CJK = ("违规", "敏感", "审核", "不合规")


def _msg_matches(msg: str, latin: tuple[str, ...], cjk: tuple[str, ...]) -> bool:
    if any(kw in msg for kw in cjk):
        return True
    return any(re.search(kw, msg, re.IGNORECASE) for kw in latin)


def _classify_by_message(msg: str) -> ProviderError:
    """Best-effort classification of a provider's plain-text error."""
    if _msg_matches(msg, _QUOTA_LATIN, _QUOTA_CJK):
        return ProviderQuotaError(msg)
    if _msg_matches(msg, _RATE_LIMIT_LATIN, _RATE_LIMIT_CJK):
        return ProviderRateLimitError(msg)
    if _msg_matches(msg, _AUTH_LATIN, _AUTH_CJK):
        return ProviderAuthError(msg)
    if _msg_matches(msg, _POLICY_LATIN, _POLICY_CJK):
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
    # Add any remaining providers not in explicit order as final fallback.
    # 过滤未配置 Key / 未开启付费 opt-in / 超预算的接口——防止显式选择
    # 免费接口失败后，自动回退链产生未授权的付费调用。
    from services.providers import (
        FREE_PROVIDERS, MULTI_KEY_PROVIDERS, OPTIONAL_KEY_PROVIDERS, PROVIDER_KEYS,
    )
    from services.generation import budget as _budget
    paid_allowed = bool(cfg.get("paid_auto_opt_in"))
    over_budget = _budget.over_budget(cfg)
    for name, fn in ALL_PROVIDERS.items():
        if name in providers or fn is None:
            continue
        if name not in FREE_PROVIDERS and (not paid_allowed or over_budget):
            continue
        required_keys = MULTI_KEY_PROVIDERS.get(name)
        if required_keys:
            if not all(str(cfg.get(k, "") or "").strip() for k in required_keys):
                continue
        else:
            key_name = PROVIDER_KEYS.get(name)
            if (key_name and name not in OPTIONAL_KEY_PROVIDERS
                    and not str(cfg.get(key_name, "") or "").strip()):
                continue
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
        # provider_id 已是注册表 stable id，付费预算/健康度按它查表；
        # 展示串（含模型名）仅用于界面与历史记录展示
        used = result.provider_id or ""
        shown = result.provider_display or used
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
        return result.image_bytes, shown

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
