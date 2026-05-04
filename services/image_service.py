"""
services/image_service.py — 图片生成调度器 + 本地落盘

改动说明（v1.1）：
- generate_image() 完全不变（txt2img 竞速降级，保持原样）
- generate_image_img2img() 重构为统一抽象层，支持 strength 参数和动态 provider 注册
- 新增 IMG2IMG_PROVIDERS 注册表，各 provider 的 try_xxx_img2img 函数按需补充
"""
import io, random, re, time
from datetime import datetime
from typing import Callable, Optional, Tuple

from PIL import Image

from config.settings import IMAGES_DIR
from services.logger import log_to_file
from services.providers import ALL_PROVIDERS, DEFAULT_ORDER


# ─── img2img Provider 注册表 ─────────────────────────────────────
# 格式：name -> (fn, description)
# fn 签名：fn(prompt, w, h, seed, source_bytes, cfg, log, strength=float) -> (bytes, str)
# key = provider 注册名，value = (img2img 函数, 是否默认启用)
IMG2IMG_PROVIDERS: dict[str, Callable] = {}

# 懒加载避免循环导入 — 首次调用时填充
_IMG2IMG_LOADED = False


def _load_img2img_providers():
    global _IMG2IMG_LOADED
    if _IMG2IMG_LOADED:
        return
    _IMG2IMG_LOADED = True

    # 按优先级顺序注册（前面的优先尝试）
    from services.providers.pollinations import try_pollinations_img2img
    from services.providers.modelslab import try_modelslab_img2img
    from services.providers.leonardoai import try_leonardo_img2img
    from services.providers.stability_ai import try_stability_img2img
    from services.providers.replicate_flux import try_replicate_img2img

    IMG2IMG_PROVIDERS["Pollinations.AI"]  = try_pollinations_img2img
    IMG2IMG_PROVIDERS["ModelsLab"]         = try_modelslab_img2img
    IMG2IMG_PROVIDERS["Leonardo.ai"]       = try_leonardo_img2img
    IMG2IMG_PROVIDERS["Stability AI"]     = try_stability_img2img
    IMG2IMG_PROVIDERS["Replicate SDXL"]   = try_replicate_img2img


# ─── txt2img（原有逻辑，完全不变）────────────────────────────────────

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


# ─── img2img 统一抽象层（v1.1 新增）───────────────────────────────

def generate_image_img2img(
    prompt: str,
    w: int, h: int,
    seed: Optional[int],
    source_bytes: bytes,
    cfg: dict,
    strength: float = 0.7,
    provider_order: list = None,
    status_cb: Callable[[str], None] = None,
    log_cb: Callable[[str], None] = None,
) -> Tuple[bytes, str]:
    """
    图生图统一调度器（v1.1 重构）。

    策略：
    1. 加载 img2img provider 注册表
    2. 若 provider_order 指定，则按指定顺序只尝试这些 provider
    3. 否则按默认优先级顺序竞速降级
    4. 每个 provider 失败后自动切换下一个
    5. 所有失败才抛异常

    参数：
        prompt       提示词
        w, h         输出尺寸
        seed         随机种子（None=随机）
        source_bytes 参考图原始字节
        cfg          配置字典
        strength     变化程度 0.1~0.9（默认 0.7）
                     0.1 = 轻微变化，0.5 = 中等，0.9 = 大幅改造
                     注意：Pollinations 不支持此参数，会自动忽略
        provider_order  可选，指定 provider 顺序
        status_cb    UI 状态回调
        log_cb       日志回调
    返回：
        (image_bytes, provider_name)
    """
    if seed is None:
        seed = random.randint(0, 2_147_483_647)
    if log_cb is None:
        log_cb = log_to_file

    _load_img2img_providers()

    # 确定尝试顺序
    if provider_order:
        # 用户指定顺序：只尝试名单中的 provider
        ordered = [(name, IMG2IMG_PROVIDERS[name])
                   for name in provider_order
                   if name in IMG2IMG_PROVIDERS]
    else:
        # 默认顺序
        ordered = list(IMG2IMG_PROVIDERS.items())

    errors = []
    for name, fn in ordered:
        try:
            if status_cb:
                status_cb(f"⏳ {name} img2img…")
            log_to_file(f"=== {name} img2img 尝试 ===")
            # 统一调用接口，通过 kwargs 兼容不同 provider 的可选参数
            data, used = fn(
                prompt, w, h, seed, source_bytes, cfg, log_cb,
                strength=strength,
            )
            log_to_file(f"✓ {name} img2img 成功")
            return data, used
        except Exception as e:
            errors.append(f"[{name}] {e}")
            log_to_file(f"⚠ {name} img2img: {e}")
            if status_cb:
                status_cb(f"⚠ {name} 失败，切换…")
            time.sleep(0.5)

    raise RuntimeError(
        "所有图生图接口均失败:\n" + "\n".join(errors)
    )


# ─── 公共工具函数（不变）────────────────────────────────────────────

def save_image_file(image_bytes: bytes, prompt: str) -> str:
    safe  = re.sub(r'[^\w\s-]', '_', prompt[:32]).strip()
    fname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}.png"
    fpath = f"{IMAGES_DIR}/{fname}"
    Image.open(io.BytesIO(image_bytes)).save(fpath, "PNG")
    return fpath
