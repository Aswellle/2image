"""注册表单一真相护栏：provider 模块注册表 ↔ 生成 manifest 一致性。

背景：manifest 曾与 PROVIDER_INFO 发生漂移（minimax 分类/名称、
openai 名称、cloudflare config_key），导致路由与可用性判断失准。
本测试把两份注册表锁进一致——变更 provider 元数据时必须同步双方。
"""
import importlib
import pkgutil

import services.providers as registry
from config.settings import DEFAULT_CONFIG
from services.generation.provider_manifest import ALL_MANIFESTS


def _provider_infos() -> dict:
    """从各 provider 模块的 PROVIDER_INFO 收集 {stable_id: info}。"""
    out = {}
    for m in pkgutil.iter_modules(registry.__path__):
        if m.name.startswith("_"):
            continue
        mod = importlib.import_module(f"services.providers.{m.name}")
        info = getattr(mod, "PROVIDER_INFO", None)
        if info:
            out[info.get("id", m.name)] = info
    return out


def test_manifest_ids_match_registry():
    assert set(ALL_MANIFESTS) == set(registry.ALL_PROVIDERS)


def test_manifest_names_match_provider_info():
    infos = _provider_infos()
    for pid, info in infos.items():
        assert ALL_MANIFESTS[pid].name == info["name"], pid


def test_manifest_categories_match_provider_info():
    infos = _provider_infos()
    for pid, info in infos.items():
        assert ALL_MANIFESTS[pid].category == info["category"], pid


def test_manifest_config_keys_match_registry():
    for pid, manifest in ALL_MANIFESTS.items():
        assert manifest.config_key == registry.PROVIDER_KEYS.get(pid), pid


def test_manifest_tiers_match_registry_partitions():
    for pid, manifest in ALL_MANIFESTS.items():
        if manifest.category == "free":
            assert pid in registry.FREE_PROVIDERS, pid
        elif manifest.category == "paid":
            assert pid in registry.PAID_PROVIDERS, pid
        else:
            assert pid in registry.COMMERCIAL_PROVIDERS, pid


def test_all_config_keys_exist_in_defaults():
    """config_key 不在 DEFAULT_CONFIG 时环境变量注入与配置读写都会静默失效。"""
    for pid, manifest in ALL_MANIFESTS.items():
        if manifest.config_key:
            assert manifest.config_key in DEFAULT_CONFIG, pid


def test_multi_key_providers_declared():
    """Cloudflare 需要 Account ID + API Token 双凭证全部就绪。"""
    assert registry.MULTI_KEY_PROVIDERS.get("cloudflare_ai") == (
        "cf_account_id", "cf_api_token")
    for pid, keys in registry.MULTI_KEY_PROVIDERS.items():
        for k in keys:
            assert k in DEFAULT_CONFIG, (pid, k)
