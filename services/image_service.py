"""
services/image_service.py — 图片生成调度器 + 本地落盘
"""
import io, os, random, re, time
from datetime import datetime
from typing import Callable, Optional, Tuple

from PIL import Image

from config.settings import IMAGES_DIR
from services.logger import log_to_file
from services.providers import ALL_PROVIDERS, DEFAULT_ORDER


def generate_image(prompt, w, h, seed, cfg,
                   provider_order=None, status_cb=None, log_cb=None,
                   ref_image: bytes | None = None,
                   strength: float = 0.6):
    """
    生成图片。

    ref_image: 参考图字节（图生图模式），None = 纯文生图。
    strength:  变化强度 0.1~0.9，越小越接近原图（仅 img2img 模式有效）。

    img2img 参数通过临时 cfg 副本传递给支持该功能的 provider，
    不影响原始 cfg（不会写入 config.json）。
    """
    if seed is None: seed = random.randint(0, 2_147_483_647)
    if log_cb is None: log_cb = log_to_file

    # 图生图：构造含临时参数的 cfg 副本，不污染原始配置
    eff_cfg = cfg
    if ref_image is not None:
        eff_cfg = {**cfg, "_ref_image": ref_image, "_ref_strength": float(strength)}
        log_to_file(f"[img2img] 参考图 {len(ref_image)//1024}KB  强度={strength:.1f}")

    order = provider_order or DEFAULT_ORDER
    errors = []
    for name in order:
        fn = ALL_PROVIDERS.get(name)
        if fn is None: continue
        try:
            if status_cb: status_cb(f"⏳ 接口: {name}…")
            log_to_file(f"=== 尝试 {name} ===")
            data, used = fn(prompt, w, h, seed, eff_cfg, log_cb)
            log_to_file(f"✓ {name} 成功")
            return data, used
        except (ValueError, RuntimeError, TimeoutError) as e:
            errors.append(f"[{name}] {type(e).__name__}: {e}")
            log_to_file(f"✗ {name}: {e}")
            if status_cb: status_cb(f"⚠ {name} 失败，切换…")
            time.sleep(0.5)
    raise RuntimeError("所有接口均失败:\n" + "\n".join(errors))


def save_image_file(image_bytes, prompt,
                    seed: int = 0, provider: str = "",
                    translated: str = "", size: str = "") -> str:
    safe  = re.sub(r'[^\w\s-]', '_', prompt[:32]).strip()
    fname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}.png"
    fpath = os.path.join(IMAGES_DIR, fname)

    img = Image.open(io.BytesIO(image_bytes))

    # Embed metadata in PNG tEXt chunks
    from PIL import PngImagePlugin
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

    img.save(fpath, "PNG", pnginfo=meta)
    return fpath
