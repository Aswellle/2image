"""tests/test_budget.py — PAY-001 预算计费器行为回归。"""

import json

import pytest

from services.generation import budget


@pytest.fixture()
def tmp_spend(tmp_path, monkeypatch):
    spend_file = tmp_path / "spend.json"
    monkeypatch.setattr(budget, "SPEND_FILE", str(spend_file))
    return spend_file


def test_estimate_cost_known_and_fallback():
    assert budget.estimate_cost("openai_image") > 0
    assert budget.estimate_cost("totally_unknown_paid") == budget.FALLBACK_ESTIMATE


def test_is_paid_classification():
    assert budget.is_paid("openai_image")
    assert budget.is_paid("ideogram")
    assert not budget.is_paid("pollinations")
    assert not budget.is_paid("siliconflow")
    assert not budget.is_paid("nonexistent")


def test_record_spend_accumulates(tmp_spend):
    cfg = {"paid_daily_budget_usd": 2.0}
    assert budget.record_spend("openai_image", cfg) == pytest.approx(0.05)
    total = budget.record_spend("openai_image", cfg)
    assert total == pytest.approx(0.10)
    data = json.loads(tmp_spend.read_text(encoding="utf-8"))
    assert list(data.values())[0]["openai_image"] == pytest.approx(0.10)


def test_record_spend_ignores_free_providers(tmp_spend):
    cfg = {"paid_daily_budget_usd": 2.0}
    before = budget.spent_today(cfg)
    budget.record_spend("pollinations", cfg)
    budget.record_spend("siliconflow", cfg)
    assert budget.spent_today(cfg) == before
    assert not tmp_spend.exists() and before == 0.0


def test_over_budget_semantics(tmp_spend):
    # 预算 0 = 不限
    assert not budget.over_budget({"paid_daily_budget_usd": 0})
    assert not budget.over_budget({})
    # 达到上限 → over
    cfg = {"paid_daily_budget_usd": 0.08}
    budget.record_spend("openai_image", cfg)  # 0.05
    assert not budget.over_budget(cfg)
    budget.record_spend("openai_image", cfg)  # 0.10 >= 0.08
    assert budget.over_budget(cfg)


def test_filter_by_budget_strips_paid_keeps_free(tmp_spend):
    cfg = {"paid_daily_budget_usd": 0.01}
    budget.record_spend("openai_image", cfg)  # 0.05 >= 0.01 → over
    order = ["openai_image", "siliconflow", "pollinations"]
    filtered = budget.filter_by_budget(order, cfg)
    assert filtered == ["siliconflow", "pollinations"]


def test_filter_by_budget_noop_when_under(tmp_spend):
    cfg = {"paid_daily_budget_usd": 100.0}
    order = ["openai_image", "pollinations"]
    assert budget.filter_by_budget(order, cfg) == order


def test_router_excludes_paid_when_over_budget(tmp_spend):
    from services.generation.router import get_provider_order

    cfg = {"sf_key": "sk", "openai_key": "sk", "paid_auto_opt_in": True, "paid_daily_budget_usd": 0.01}
    budget.record_spend("openai_image", cfg)
    order = get_provider_order("banner 标题", cfg)
    assert "openai_image" not in order
    assert "siliconflow" in order  # 免费兜底仍在


def test_estimate_history_cost_maps_display_names(in_memory_db):
    """历史花费估算：展示串（manifest 名 + "/模型" 后缀）映射回 stable id 查单价。"""
    from data import repository
    from services.generation import budget

    repository.add_entry("a", "", "/tmp/a.png", "Pollinations/flux")
    repository.add_entry("b", "", "/tmp/b.png", "OpenAI/gpt-image-2.6-flare-standard")
    repository.add_entry("c", "", "/tmp/c.png", "OpenAI/gpt-image-2.6-flare-hd")
    repository.add_entry("d", "", "/tmp/d.png", "未知供应商字符串")
    est = budget.estimate_history_cost()
    assert est["count"] == 4
    assert est["paid_count"] == 2
    assert est["total"] == pytest.approx(0.10)
    assert est["avg"] == pytest.approx(0.05)
    assert est["by_provider"]["openai_image"]["count"] == 2
    # 免费接口不进花费分布
    assert "pollinations" not in est["by_provider"]


def test_resolve_display_prefix_longest_match():
    """最长前缀匹配：Nano-Banana-Pro 不被通用 Gemini 前缀吞掉。"""
    from services.generation import budget

    assert budget.resolve_display_to_id("Gemini/Nano-Banana-Pro") == "gemini_nano_banana_pro"
    assert budget.resolve_display_to_id("Gemini/2.5-flash-image") == "gemini"
    assert budget.resolve_display_to_id("豆包/doubao-seedream-5-5-261028") == "volcengine_ark"
    assert budget.resolve_display_to_id("Pollinations.AI (免费·无需Key)") == "pollinations"  # 旧版遗留名
    assert budget.resolve_display_to_id("完全未知的串") is None
    assert budget.resolve_display_to_id("") is None


def test_estimate_history_cost_empty(in_memory_db):
    from services.generation import budget

    est = budget.estimate_history_cost()
    assert est["total"] == 0.0
    assert est["paid_count"] == 0
    assert est["avg"] == 0.0
    assert est["by_provider"] == {}


def test_parse_budget_input_accepts_finite_values():
    assert budget.parse_budget_input("5.5") == pytest.approx(5.5)
    assert budget.parse_budget_input("") == 0.0
    assert budget.parse_budget_input("0") == 0.0
    assert budget.parse_budget_input(2) == pytest.approx(2.0)


def test_parse_budget_input_rejects_non_finite_and_negative():
    for raw in ("nan", "inf", "-inf", "-1", "abc", None):
        assert budget.parse_budget_input(raw) is None, raw


def test_parse_budget_input_uses_default_for_init_display():
    assert budget.parse_budget_input("abc", default=2.0) == 2.0
    assert budget.parse_budget_input(float("nan"), default=2.0) == 2.0
    assert budget.parse_budget_input(-3, default=2.0) == 2.0
