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


def test_img2img_flags_match_registry():
    """supports_img2img 必须在两份注册表里一致。

    IMG2IMG_PROVIDERS 只从 PROVIDER_INFO 构建，而路由与 UI 读的是
    manifest；两者不一致时，实现了参考图逻辑的接口会从图生图下拉框
    里静默消失（历史事故：gemini / openai_image / minimax_image /
    volcengine_ark 四个接口因此长期不可选）。
    """
    for pid, manifest in ALL_MANIFESTS.items():
        assert manifest.supports_img2img == (pid in registry.IMG2IMG_PROVIDERS), pid


def test_img2img_providers_are_registered():
    """IMG2IMG_PROVIDERS 的每个 id 都必须真实存在于 provider 注册表。"""
    unknown = set(registry.IMG2IMG_PROVIDERS) - set(registry.ALL_PROVIDERS)
    assert not unknown, unknown


def test_wizard_configured_matches_actual_wizards():
    """WIZARD_CONFIGURED 必须与两个向导实际写入的配置键一致。

    这张表决定哪些接口会出现在需要先配 Key 的下拉框里。手工维护
    极易漂移（历史事故：volcengine_ark 有卡片却被排除、xai_grok
    没有卡片却被列入），因此直接从向导源码里提取写入的键来比对。
    """
    import re
    from pathlib import Path

    from services.providers import MULTI_KEY_PROVIDERS

    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    written: set[str] = set()
    for name in ("wizard_free.py", "wizard_paid.py"):
        src = (ui_dir / name).read_text(encoding="utf-8")
        written |= set(re.findall(r'cfg\["([a-z_]+)"\]', src))

    infos = _provider_infos()
    for pid, info in infos.items():
        keys = MULTI_KEY_PROVIDERS.get(pid) or (
            (info["config_key"],) if info.get("config_key") else ())
        covered = all(k in written for k in keys) if keys else True
        assert (pid in registry.WIZARD_CONFIGURED) == covered, pid
