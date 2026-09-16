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

from PIL import Image, PngImagePlugin

from config.settings import IMAGES_DIR

from services.generation.cancellation import CancellationToken
from services.generation.downloader import bounded_download
from services.generation.errors import (
    DeadlineExceeded,
    GenerationCancelled,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTransientError,
)
from services.generation.orchestrator import GenerationOrchestrator
from services.logger import log_to_file
from services.providers import ALL_PROVIDERS, DEFAULT_ORDER


def _wrap_provider_fn(fn: Callable) -> Callable:
    """Map provider exceptions to ProviderError taxonomy.

    Existing providers raise ValueError/RuntimeError; the orchestrator needs
    ProviderError to make correct fallback decisions (e.g. 401 → don't retry).
    """
    def wrapped(prompt, width, height, seed, cfg, log_cb):
        try:
            return fn(prompt, width, height, seed, cfg, log_cb)
        except (ProviderError, GenerationCancelled):
            raise  # Already domain errors, don't re-wrap
        except Exception as exc:
            msg = str(exc)
            lowered = msg.lower()
            # Map auth-related errors (missing/invalid API key)
            if "key" in lowered and any(
                kw in lowered for kw in ("api", "需要", "无效", "invalid", "missing", "required")
            ):
                raise ProviderAuthError(msg) from exc
            # Map rate-limit related errors
            if any(kw in lowered for kw in ("rate", "429", "limit", "限流", "too many")):
                raise ProviderRateLimitError(msg) from exc
            # Default: transient (will be retried by orchestrator, then fallback)
            raise ProviderTransientError(f"{type(exc).__name__}: {exc}") from exc
    wrapped.__name__ = getattr(fn, "__name__", "wrapped_provider")
    return wrapped


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
        return result.image_bytes, result.provider_id or ""

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
