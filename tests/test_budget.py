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
    budget.record_spend("openai_image", cfg)   # 0.05
    assert not budget.over_budget(cfg)
    budget.record_spend("openai_image", cfg)   # 0.10 >= 0.08
    assert budget.over_budget(cfg)


def test_filter_by_budget_strips_paid_keeps_free(tmp_spend):
    cfg = {"paid_daily_budget_usd": 0.01}
    budget.record_spend("openai_image", cfg)   # 0.05 >= 0.01 → over
    order = ["openai_image", "siliconflow", "pollinations"]
    filtered = budget.filter_by_budget(order, cfg)
    assert filtered == ["siliconflow", "pollinations"]


def test_filter_by_budget_noop_when_under(tmp_spend):
    cfg = {"paid_daily_budget_usd": 100.0}
    order = ["openai_image", "pollinations"]
    assert budget.filter_by_budget(order, cfg) == order


def test_router_excludes_paid_when_over_budget(tmp_spend):
    from services.generation.router import get_provider_order
    cfg = {"sf_key": "sk", "openai_key": "sk",
           "paid_auto_opt_in": True, "paid_daily_budget_usd": 0.01}
    budget.record_spend("openai_image", cfg)
    order = get_provider_order("banner 标题", cfg)
    assert "openai_image" not in order
    assert "siliconflow" in order  # 免费兜底仍在
