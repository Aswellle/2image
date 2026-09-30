"""
tests/test_gap_fixes.py — 《全面代码审查与开发修复优化计划》差距修复回归
──────────────────────────────────────────────────────────────────────
覆盖本轮差距弥合的关键行为：
  · orchestrator fallback=False 语义（invalid_request 终止链）
  · orchestrator 认证错误穿透到下一 provider + 取消立即返回
  · _wrap_provider_fn 边界分类（HTTPError/缺key/配额/策略）
  · smart_router 缺 key 免费接口过滤 + PAY-001 付费 opt-in
  · FTS5 触发器增量维护 + CJK/拉丁关键词分流
  · PRAGMA user_version 版本化迁移
  · 字体 SHA256 校验
"""
import sqlite3

import pytest
import requests

from config.settings import DEFAULT_CONFIG
from data import repository as repo
from data.repository import _set_test_db
from services.generation.cancellation import CancellationToken
from services.generation.errors import (
    GenerationCancelled,
    ProviderAuthError,
    ProviderInvalidRequestError,
    ProviderPolicyError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderTransientError,
)
from services.generation.orchestrator import GenerationOrchestrator
from services.image_service import _wrap_provider_fn
from services.smart_router import _filter_available


# ── Orchestrator fallback 语义 ────────────────────────────────

def _ok_provider(prompt, w, h, seed, cfg, log):
    return b"image", "ok_provider"


def _make_providers(*behaviors):
    """behaviors: list of exception-or-None; None = success."""
    fns = {}
    for i, behavior in enumerate(behaviors):
        name = f"prov_{i}"
        def make_fn(b):
            def fn(prompt, w, h, seed, cfg, log):
                if isinstance(b, Exception):
                    raise b
                return b"image", "me"
            return fn
        fns[name] = make_fn(behavior)
    return fns


def test_orchestrator_invalid_request_stops_chain():
    """fallback=False（参数错误）→ 不再撞其余 provider（NET-001 验收）。"""
    providers = _make_providers(
        ProviderInvalidRequestError("bad size"),
        _ok_provider,
        _ok_provider,
    )
    orch = GenerationOrchestrator(providers=providers, retry_policy=__import__(
        "services.generation.retry_policy", fromlist=["RetryPolicy"]).RetryPolicy(max_attempts=2))
    result = orch.run("p", 64, 64, 1, {})
    assert result.image_bytes is None
    assert len(result.errors) == 1  # 只试了第一家


def test_orchestrator_auth_error_falls_through():
    """认证错误 → 不重试本 provider，但继续下一家。"""
    providers = _make_providers(
        ProviderAuthError("401 unauthorized"),
        _ok_provider,
    )
    orch = GenerationOrchestrator(
        providers=providers,
        retry_policy=__import__(
            "services.generation.retry_policy", fromlist=["RetryPolicy"]).RetryPolicy(max_attempts=3),
    )
    result = orch.run("p", 64, 64, 1, {})
    assert result.image_bytes == b"image"


def test_orchestrator_cancel_returns_immediately():
    """取消令牌 → orchestrator 立即返回 cancelled（JOB-001 ≤500ms）。"""
    providers = _make_providers(_ok_provider)
    orch = GenerationOrchestrator(providers=providers)
    token = CancellationToken()
    token.cancel()
    with pytest.raises(GenerationCancelled):
        orch.run("p", 64, 64, 1, {}, token=token)


def test_orchestrator_transient_retries_then_fallback():
    providers = _make_providers(
        ProviderTransientError("503"), ProviderTransientError("503"),
        _ok_provider,
    )
    from services.generation.retry_policy import RetryPolicy
    orch = GenerationOrchestrator(
        providers=providers,
        retry_policy=RetryPolicy(max_attempts=1, base_delay=0.01),
    )
    result = orch.run("p", 64, 64, 1, {})
    assert result.image_bytes == b"image"


# ── _wrap_provider_fn 分类边界 ─────────────────────────────────

def test_wrap_maps_missing_token_to_auth():
    """缺 Token（不只 Key）→ ProviderAuthError（不再当 transient 重试）。"""
    def fn(prompt, w, h, seed, cfg, log):
        raise ValueError("需要填写 HuggingFace Token")
    err = None
    try:
        _wrap_provider_fn(fn)("p", 64, 64, 1, {}, None)
    except ProviderAuthError as exc:
        err = exc
    assert err is not None


def test_wrap_maps_http_429():
    def fn(prompt, w, h, seed, cfg, log):
        resp = requests.models.Response()
        resp.status_code = 429
        raise requests.HTTPError("429", response=resp)
    with pytest.raises(ProviderRateLimitError):
        _wrap_provider_fn(fn)("p", 64, 64, 1, {}, None)


def test_wrap_maps_quota_and_policy():
    def quota_fn(prompt, w, h, seed, cfg, log):
        raise RuntimeError("账户余额不足，请充值")
    with pytest.raises(ProviderQuotaError):
        _wrap_provider_fn(quota_fn)("p", 64, 64, 1, {}, None)

    def policy_fn(prompt, w, h, seed, cfg, log):
        raise RuntimeError("content policy violation")
    with pytest.raises(ProviderPolicyError):
        _wrap_provider_fn(policy_fn)("p", 64, 64, 1, {}, None)


def test_wrap_maps_timeout_to_transient():
    def fn(prompt, w, h, seed, cfg, log):
        raise requests.Timeout("timed out")
    with pytest.raises(ProviderTransientError):
        _wrap_provider_fn(fn)("p", 64, 64, 1, {}, None)


# ── smart_router：缺 key 过滤 + PAY-001 ───────────────────────

def test_router_filters_free_provider_without_key():
    """缺 key 的免费接口被过滤（不再每次生成空跑 3 轮重试）。"""
    cfg = dict(DEFAULT_CONFIG)  # 全空 key
    order = ["siliconflow", "pollinations", "stablehorde"]
    assert _filter_available(order, cfg) == ["pollinations", "stablehorde"]


def test_router_keeps_free_provider_with_key():
    cfg = dict(DEFAULT_CONFIG)
    cfg["sf_key"] = "sk-xxx"
    assert "siliconflow" in _filter_available(["siliconflow", "pollinations"], cfg)


def test_router_paid_requires_opt_in():
    """PAY-001: 已配置付费 key 也不自动路由，opt-in 后才进入。"""
    cfg = dict(DEFAULT_CONFIG)
    cfg["openai_key"] = "sk-paid"
    assert "openai_image" not in _filter_available(["openai_image", "pollinations"], cfg)
    assert "openai_image" in _filter_available(
        ["openai_image", "pollinations"], cfg, allow_paid=True)


def test_router_stablehorde_key_optional():
    cfg = dict(DEFAULT_CONFIG)
    assert "stablehorde" in _filter_available(["stablehorde"], cfg)


# ── FTS5 触发器 + 关键词分流 ──────────────────────────────────

@pytest.fixture()
def mem_db():
    _set_test_db(":memory:")
    repo.init_db()
    yield repo
    _set_test_db(":memory:")
    repo.init_db()


def test_fts_latin_vs_cjk_split(mem_db):
    mem_db.add_entry("a cute cat on the moon", "月亮上的猫", "", "t")
    mem_db.add_entry("赛博朋克城市夜景", "", "", "t")
    assert len(mem_db.get_all_entries(keyword="cat")) == 1       # FTS
    assert len(mem_db.get_all_entries(keyword="赛博")) == 1      # LIKE
    assert mem_db.get_all_entries(keyword="zzz_no_match") == []


def test_fts_trigger_maintenance_on_delete(mem_db):
    e = mem_db.add_entry("unique_zebra_prompt", "", "", "t")
    assert len(mem_db.get_all_entries(keyword="zebra")) == 1
    mem_db.delete_entry(e["id"], remove_file=False)
    assert mem_db.get_all_entries(keyword="zebra") == []


def test_fts_trigger_maintenance_on_update(mem_db):
    e = mem_db.add_entry("original_dog_prompt", "", "", "t")
    conn = repo._conn()
    conn.execute("UPDATE history SET prompt='revised_fox_prompt' WHERE id=?", (e["id"],))
    conn.commit()
    assert mem_db.get_all_entries(keyword="fox") and not mem_db.get_all_entries(keyword="dog")


def test_user_version_migration_applied(mem_db):
    conn = repo._conn()
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == 1
    # 幂等：重复 init_db 不变
    repo.init_db()
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


# ── 字体 SHA256 校验 ──────────────────────────────────────────

def test_font_verify_rejects_hash_mismatch():
    from config.fonts import _verify
    entry = {"sha256": "0" * 64, "min_bytes": 10, "max_bytes": 1000}
    assert not _verify(b"x" * 100, entry)
    ok_entry = {"min_bytes": 10, "max_bytes": 1000}
    assert _verify(b"x" * 100, ok_entry)


def test_font_verify_rejects_wrong_size():
    from config.fonts import _verify
    entry = {"min_bytes": 1000, "max_bytes": 2000}
    assert not _verify(b"x" * 10, entry)
    assert not _verify(b"x" * 5000, entry)
