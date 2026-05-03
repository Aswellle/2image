"""
services/image_service.py — 图片生成调度器 + 本地落盘
"""
import io, random, re, time
from datetime import datetime
from typing import Callable, Optional, Tuple

from PIL import Image

from config.settings import IMAGES_DIR
from services.logger import log_to_file
from services.providers import ALL_PROVIDERS, DEFAULT_ORDER


def generate_image(
    prompt: str,
    w: int, h: int,
    seed: Optional[int],
    cfg: dict,
    provider_order: list = None,
    status_cb: Callable[[str], None] = None,
    log_cb: Callable[[str], None] = None,
) -> Tuple[bytes, str]:
    if seed is None:
        seed = random.randint(0, 2_147_483_647)
    if log_cb is None:
        log_cb = log_to_file
    order = provider_order or DEFAULT_ORDER
    errors = []

    for name in order:
        fn = ALL_PROVIDERS.get(name)
        if fn is None:
            continue
        try:
            if status_cb:
                status_cb(f"⏳ 接口: {name}…")
            log_to_file(f"=== 尝试 {name} ===")
            data, used = fn(prompt, w, h, seed, cfg, log_cb)
            log_to_file(f"✓ {name} 成功")
            return data, used
        except Exception as e:
            errors.append(f"[{name}] {e}")
            log_to_file(f"✗ {name}: {e}")
            if status_cb:
                status_cb(f"⚠ {name} 失败，切换…")
            time.sleep(0.5)

    raise RuntimeError("所有接口均失败:\n" + "\n".join(errors))


def generate_image_img2img(
    prompt: str,
    w: int, h: int,
    seed: Optional[int],
    source_bytes: bytes,
    cfg: dict,
    provider_order: list = None,
    status_cb: Callable[[str], None] = None,
    log_cb: Callable[[str], None] = None,
) -> Tuple[bytes, str]:
    """
    图生图：尝试各支持 img2img 的 Provider。
    目前支持：Pollinations.AI、ModelsLab、Stability AI（部分）。
    """
    if seed is None:
        seed = random.randint(0, 2_147_483_647)
    if log_cb is None:
        log_cb = log_to_file

    # 图生图专用顺序（支持 img2img 的优先）
    IMG2IMG_ORDER = [
        ("Pollinations.AI (img2img)", "pollinations_img2img"),
        ("ModelsLab (img2img)",      "modelslab_img2img"),
    ]

    errors = []

    # 首先尝试直接从 Pollinations 图生图
    try:
        from services.providers.pollinations import try_pollinations_img2img
        if status_cb:
            status_cb(f"⏳ Pollinations img2img…")
        data, used = try_pollinations_img2img(
            prompt, w, h, seed, source_bytes, cfg, log_cb)
        log_to_file(f"✓ Pollinations img2img 成功")
        return data, used
    except Exception as e:
        errors.append(f"[Pollinations img2img] {e}")
        log_to_file(f"⚠ Pollinations img2img: {e}")

    # 其次尝试 ModelsLab img2img
    try:
        from services.providers.modelslab import try_modelslab_img2img
        if status_cb:
            status_cb(f"⏳ ModelsLab img2img…")
        data, used = try_modelslab_img2img(
            prompt, w, h, seed, source_bytes, cfg, log_cb)
        log_to_file(f"✓ ModelsLab img2img 成功")
        return data, used
    except Exception as e:
        errors.append(f"[ModelsLab img2img] {e}")
        log_to_file(f"⚠ ModelsLab img2img: {e}")

    raise RuntimeError("所有图生图接口均失败:\n" + "\n".join(errors))


def save_image_file(image_bytes: bytes, prompt: str) -> str:
    safe  = re.sub(r'[^\w\s-]', '_', prompt[:32]).strip()
    fname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}.png"
    fpath = f"{IMAGES_DIR}/{fname}"
    Image.open(io.BytesIO(image_bytes)).save(fpath, "PNG")
    return fpath
