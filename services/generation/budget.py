"""
services/generation/budget.py — 付费预算守卫（PAY-001 后半）
────────────────────────────────────────────────────────────
"保存了 Key" ≠ "授权无限消费"。本模块按天累计付费接口的
**估算**消耗（USD），超过日预算时：

  · 自动路由：直接把付费/商业接口从候选中剔除（静默降级到免费）
  · 显式选择付费接口：由 GenerationController 弹窗阻断

存储：~/2image/spend.json（按天分桶，启动/记录时清理过期天）。
单价为保守近似的**估算值**，仅用于预算守卫，不构成账单依据。
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime

from config.settings import APP_DIR

log = logging.getLogger(__name__)

SPEND_FILE = os.path.join(APP_DIR, "spend.json")

# 估算单价（USD / 张）。取各供应商主流模型 1024x1024 档的公开定价近似值，
# 偏高取整 —— 预算守卫宁可早停。新付费供应商接入时在此补一行。
PRICING_USD_PER_IMAGE: dict[str, float] = {
    "openai_image": 0.05,             # gpt-image-1 medium
    "stability_ai": 0.04,             # core
    "replicate_flux": 0.04,           # flux-1.1-pro
    "xai_grok": 0.03,
    "ideogram": 0.08,
    "fal_flux": 0.06,                 # FLUX pro ultra
    "recraft": 0.04,
    "bfl_flux": 0.05,                 # flux-pro
    "minimax_image": 0.05,
    "gemini_nano_banana_pro": 0.15,   # Gemini 3 Pro Image
    "volcengine_ark": 0.05,           # Seedream
}

# 不在定价表中的付费接口按此兜底估算
FALLBACK_ESTIMATE = 0.05

_LOCK = threading.Lock()


def estimate_cost(provider_id: str) -> float:
    """单张图估算成本（USD）；免费接口返回 0。"""
    return PRICING_USD_PER_IMAGE.get(provider_id, FALLBACK_ESTIMATE)


def is_paid(provider_id: str) -> bool:
    """是否付费/商业供应商（按注册表分类）。"""
    from services.providers import ALL_PROVIDERS, FREE_PROVIDERS
    return provider_id in ALL_PROVIDERS and provider_id not in FREE_PROVIDERS


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def load_spend() -> dict:
    """读取 spend.json；结构 {"YYYY-MM-DD": {"provider_id": usd}}。"""
    try:
        with open(SPEND_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _save_spend(data: dict) -> None:
    try:
        os.makedirs(APP_DIR, mode=0o700, exist_ok=True)
        tmp = SPEND_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, SPEND_FILE)  # 原子写
    except OSError as exc:
        log.warning("Failed to persist spend ledger: %s", exc)


def _prune(data: dict) -> dict:
    """只保留今天（历史天不再参与预算，直接丢弃）。"""
    today = _today()
    return {day: prov for day, prov in data.items() if day == today}


def spent_today(cfg: dict | None = None) -> float:
    """今日已记录的付费估算消耗（USD）。"""
    data = _prune(load_spend())
    return float(sum(data.get(_today(), {}).values()))


def record_spend(provider_id: str, cfg: dict | None = None) -> float:
    """成功生成后记录一次估算消耗，返回今日累计（USD）。免费接口为 no-op。"""
    if not is_paid(provider_id):
        return spent_today(cfg)
    cost = estimate_cost(provider_id)
    with _LOCK:
        data = _prune(load_spend())
        day = data.setdefault(_today(), {})
        day[provider_id] = round(day.get(provider_id, 0.0) + cost, 4)
        _save_spend(data)
    total = float(sum(data[_today()].values()))
    log.debug("Budget: %s +$%.2f → today $%.2f", provider_id, cost, total)
    return total


def daily_budget(cfg: dict) -> float:
    """日预算上限（USD）；<=0 表示不限。"""
    try:
        return float(cfg.get("paid_daily_budget_usd", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def over_budget(cfg: dict) -> bool:
    """今日消耗是否已达/超过日预算（预算<=0 = 不限 → 永不超）。"""
    limit = daily_budget(cfg)
    if limit <= 0:
        return False
    return spent_today(cfg) >= limit


def filter_by_budget(order: list[str], cfg: dict) -> list[str]:
    """预算过滤：超预算时把付费接口从自动路由候选中剔除（免费不受影响）。"""
    if not over_budget(cfg):
        return order
    kept = [pid for pid in order if not is_paid(pid)]
    if len(kept) != len(order):
        log.info("Budget reached ($%.2f): paid providers excluded from auto route",
                 spent_today(cfg))
    return kept
