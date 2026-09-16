"""
services/providers/__init__.py
Provider 注册表  v8 — 自动发现 + stable provider_id
─────────────────────
v8 重构：
  · 使用 stable provider_id 作为 ALL_PROVIDERS / DEFAULT_ORDER 的 key
  · 保留 _NAME_TO_ID 映射，兼容旧的 display-name 查找
  · DEFAULT_ORDER 改为 FREE_PROVIDER_ORDER 显式列表

v7 历史：
  · 使用 pkgutil 自动扫描 provider 模块
  · 各模块通过 PROVIDER_INFO 声明自身元信息
"""
import pkgutil
import importlib

FREE_PROVIDERS: dict[str, callable] = {}
PAID_PROVIDERS: dict[str, callable] = {}
COMMERCIAL_PROVIDERS: dict[str, callable] = {}

# stable_id → config_key (None = no key required)
PROVIDER_KEYS: dict[str, str | None] = {}

# stable_id → try_fn (img2img providers only)
IMG2IMG_PROVIDERS: dict[str, callable] = {}

# Display name → stable_id (for backward compatibility)
_NAME_TO_ID: dict[str, str] = {}

_for_loop_registry = {
    "free": FREE_PROVIDERS,
    "paid": PAID_PROVIDERS,
    "commercial": COMMERCIAL_PROVIDERS,
}

for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
    if module_name.startswith("_"):
        continue
    try:
        mod = importlib.import_module(f".{module_name}", __package__)
    except Exception as e:
        print(f"[warn] 加载 {module_name} 失败: {e}")
        continue

    info = getattr(mod, "PROVIDER_INFO", None)
    if info is None:
        continue

    # Prefer stable "id", fall back to module_name
    stable_id = info.get("id", module_name)
    display_name = info.get("name", module_name)

    try_fn_name = info.get("try_fn", f"try_{module_name}")
    try_fn = getattr(mod, try_fn_name, None)
    if try_fn is None:
        print(f"[warn] {module_name} 中未找到 {try_fn_name}")
        continue

    category = info.get("category", "free")
    if category in _for_loop_registry:
        _for_loop_registry[category][stable_id] = try_fn

    # Mappings
    PROVIDER_KEYS[stable_id] = info.get("config_key")
    _NAME_TO_ID[display_name] = stable_id

    if info.get("supports_img2img"):
        IMG2IMG_PROVIDERS[stable_id] = try_fn

ALL_PROVIDERS = {**FREE_PROVIDERS, **PAID_PROVIDERS, **COMMERCIAL_PROVIDERS}

# Explicit free-provider order (not pkgutil-dependent)
DEFAULT_ORDER = [
    "pollinations",
    "siliconflow",
    "gemini",
    "cloudflare_ai",
    "modelslab",
    "segmind",
    "openrouter",
    "huggingface",
    "stablehorde",
    "together_ai",
    "dashscope_qwen",
    "bria_ai",
]


def resolve_provider_id(name_or_id: str) -> str | None:
    """Convert a legacy display name or stable ID to a stable ID."""
    if name_or_id in ALL_PROVIDERS:
        return name_or_id
    return _NAME_TO_ID.get(name_or_id)
