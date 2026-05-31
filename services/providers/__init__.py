"""
services/providers/__init__.py
Provider 注册表  v7 — 自动发现
─────────────────────
v7 重构：
  · 使用 pkgutil 自动扫描 provider 模块，不再硬编码 import
  · 各模块通过 PROVIDER_INFO 声明自身元信息
  · 按 category 自动分类到 FREE / PAID / COMMERCIAL

v6 历史：
  · 商业变现接口（ideogram, fal_flux, recraft）防御性导入
  · 单个文件损坏不影响整体启动

v5 历史：
  · Together AI, Gemini, OpenRouter, xAI Grok 新增
"""
import pkgutil
import importlib

FREE_PROVIDERS = {}
PAID_PROVIDERS = {}
COMMERCIAL_PROVIDERS = {}

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

    try_fn_name = info.get("try_fn", f"try_{module_name}")
    try_fn = getattr(mod, try_fn_name, None)
    if try_fn is None:
        print(f"[warn] {module_name} 中未找到 {try_fn_name}")
        continue

    category = info.get("category", "free")
    if category in _for_loop_registry:
        _for_loop_registry[category][info["name"]] = try_fn

ALL_PROVIDERS = {**FREE_PROVIDERS, **PAID_PROVIDERS, **COMMERCIAL_PROVIDERS}
DEFAULT_ORDER = list(FREE_PROVIDERS.keys())
