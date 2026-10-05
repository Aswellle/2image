"""
services/generation/router.py — Health-aware scoring router v3（生产路由入口）
──────────────────────────────────────────────────────────────────────────────
Phase 3 完成：原 smart_router.py 的场景/模板/关键词语义已迁入
services/generation/scenes.py，过滤与健康感知排序在此统一执行：

  1. 场景路由（模板 ID > 关键词推断）给出候选及其产品优先级
  2. _filter_available：key 可用性（免费+付费）+ PAY-001 付费 opt-in
  3. _demote_unhealthy：按熔断状态/延迟将不健康接口降级到队尾
     （OPEN 的接口保留在末尾 —— cooldown 过后仍可作最后兜底，
      熔断期间由 orchestrator 负责跳过）
  4. 保证 Pollinations 兜底

smart_router.get_provider_order 保留为兼容层，生产代码应直接 import 本模块。
"""
from __future__ import annotations

import logging

from services.generation import scenes
from services.generation.provider_health import get_health_registry, HealthState
from services.generation.provider_manifest import (
    ALL_MANIFESTS,
    COMMERCIAL_MANIFESTS,
    FREE_MANIFESTS,
    PAID_MANIFESTS,
    ProviderManifest,
    resolve_provider_id,
)
from services.providers import (
    DEFAULT_ORDER,
    FREE_PROVIDERS,
    MULTI_KEY_PROVIDERS,
    OPTIONAL_KEY_PROVIDERS,
    PROVIDER_KEYS,
)

log = logging.getLogger(__name__)

# stable_id -> config_key for providers that require a key
_KEY_MAP: dict = {name: key for name, key in PROVIDER_KEYS.items() if key}

# set of free provider ids (no key required or key is None)
_FREE_PROVIDERS: set = set(FREE_PROVIDERS.keys())


def _has_key(name: str, cfg: dict) -> bool:
    """A provider is key-ready when it needs no key, its key is optional
    (e.g. StableHorde anonymous), or a non-empty key is configured."""
    key = _KEY_MAP.get(name)
    if not key or name in OPTIONAL_KEY_PROVIDERS:
        return True
    return bool(str(cfg.get(key, "") or "").strip())


def _filter_available(order: list, cfg: dict, allow_paid: bool | None = None) -> list:
    """过滤掉当前配置下不可用的接口。

    规则（PAY-001 / ROUTE-001）：
      1. 任何需要 Key 的接口（免费或付费），未配置 Key 就跳过 ——
         避免自动路由反复撞击缺 Key 的接口（每次触发 3 轮无谓重试）。
      2. 付费/商业接口仅在用户显式 opt-in（cfg["paid_auto_opt_in"]）时
         才进入自动路由；显式下拉选择不受此限制。
      3. 付费日预算用尽时，付费接口同样被剔除（静默降级到免费）。
    """
    from services.generation import budget

    if allow_paid is None:
        allow_paid = bool(cfg.get("paid_auto_opt_in", False))
    result = []
    for name in order:
        if not _has_key(name, cfg):
            continue
        if name not in _FREE_PROVIDERS and not allow_paid:
            continue
        result.append(name)
    return budget.filter_by_budget(result, cfg)


def _demote_unhealthy(order: list) -> list:
    """ROUTE-003: 按健康状态重排 —— 稳定路由优先级为主序，健康罚分为副序。

    罚分：DEGRADED +50 / HALF_OPEN +25 / OPEN +1000（沉底），
    另加延迟罚分 min(10, avg_latency_ms/500)。同罚分保持原顺序（稳定）。
    """
    reg = get_health_registry()

    def sort_key(pair):
        idx, pid = pair
        health = reg.get(pid)
        penalty = 0.0
        if health.state == HealthState.OPEN:
            penalty += 1000.0
        elif health.state == HealthState.DEGRADED:
            penalty += 50.0
        elif health.state == HealthState.HALF_OPEN:
            penalty += 25.0
        if health.avg_latency_ms > 0:
            penalty += min(10.0, health.avg_latency_ms / 500.0)
        return (penalty, idx)

    return [pid for _, pid in sorted(enumerate(order), key=sort_key)]


def get_provider_order(
    prompt: str = "",
    cfg: dict | None = None,
    template_id: str = "",
    fallback_order: list | None = None,
) -> list:
    """
    返回针对当前请求的最优接口优先序列。

    Parameters
    ----------
    prompt        : 用户提示词（用于关键词检测）
    cfg           : 配置字典（key 可用性 + 付费 opt-in + 预算）
    template_id   : 当前模板ID（优先于关键词检测）
    fallback_order: 兜底顺序，None 时使用 DEFAULT_ORDER

    Returns
    -------
    list[str]  稳定 provider_id 列表，至少包含一个免费兜底接口
    """
    cfg = cfg or {}

    # 1. 场景路由：模板 ID 最优先，其次关键词推断
    scene = scenes.scene_for_template(template_id) or scenes.detect_scene(prompt)
    base = scenes.route_for(scene)
    # 把未在场景列表中的接口追加到末尾（保证完整兜底）
    for name in (fallback_order or DEFAULT_ORDER):
        if name not in base:
            base.append(name)

    # 2. 可用性过滤
    available = _filter_available(base, cfg)

    # 3. 健康降级排序
    available = _demote_unhealthy(available)

    # 4. 保证最终列表非空
    if not available:
        available = ["pollinations"]

    return available


class Router:
    """
    能力/健康评分路由（manifest 驱动，与场景路由互补）。

    用于需要按能力过滤的场景（如 img2img）或显式指定 provider：

        router = Router(cfg={"sf_key": "xxx", ...})
        order = router.get_order(
            prompt="a cat",
            prefer_paid=False,
            require_img2img=False,
        )
    """

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    def get_order(
        self,
        prompt: str = "",
        prefer_paid: bool = False,
        require_img2img: bool = False,
        explicit_provider: str | None = None,
        limit: int | None = None,
    ) -> list[str]:
        """
        Return a priority-ordered list of provider IDs.

        Decision chain:
        1. Explicit provider selected → return it if capable
        2. Filter by capability (img2img, etc.)
        3. Filter by key availability
        4. Filter by free/paid policy
        5. Score by health, latency, user priority
        6. Sort by score descending
        """
        health_reg = get_health_registry()

        # 1. Explicit provider selection
        if explicit_provider:
            pid = resolve_provider_id(explicit_provider)
            if pid and pid in ALL_MANIFESTS:
                manifest = ALL_MANIFESTS[pid]
                if self._is_available(manifest, require_img2img, prefer_paid):
                    return [pid]
            # Fall through if explicit provider not available

        # 2-4. Filter candidates
        candidates: list[tuple[str, float]] = []

        # Determine which tiers to include
        tiers = [FREE_MANIFESTS]
        if prefer_paid:
            tiers.append(PAID_MANIFESTS)
            tiers.append(COMMERCIAL_MANIFESTS)

        for tier in tiers:
            for pid, manifest in tier.items():
                if not self._is_available(manifest, require_img2img, prefer_paid):
                    continue

                score = self._score_provider(manifest, health_reg)
                candidates.append((pid, score))

        # 6. Sort by score (descending), then by manifest order as tiebreaker
        candidates.sort(key=lambda x: (-x[1], x[0]))

        order = [pid for pid, _ in candidates]

        # Always include Pollinations as ultimate fallback (if capable)
        if "pollinations" not in order and "pollinations" in FREE_MANIFESTS:
            pollinations = FREE_MANIFESTS["pollinations"]
            if not require_img2img or pollinations.supports_img2img:
                if not pollinations.config_key or self.cfg.get(pollinations.config_key):
                    order.append("pollinations")

        if limit:
            order = order[:limit]

        return order

    def _is_available(
        self,
        manifest: ProviderManifest,
        require_img2img: bool,
        prefer_paid: bool,
    ) -> bool:
        """Check if a provider is available for selection."""
        # Capability check
        if require_img2img and not manifest.supports_img2img:
            return False

        # Key check — 多键接口要求全部凭证就绪（如 Cloudflare 双凭证）
        required_keys = MULTI_KEY_PROVIDERS.get(manifest.id)
        if required_keys:
            if not all(str(self.cfg.get(k, "") or "").strip()
                       for k in required_keys):
                return False
        elif manifest.config_key and not self.cfg.get(manifest.config_key):
            return False

        # Commercial providers need explicit opt-in
        if manifest.category == "commercial" and not prefer_paid:
            return False

        return True

    def _score_provider(
        self,
        manifest: ProviderManifest,
        health_reg,
    ) -> float:
        """
        Score a provider for routing priority.

        Score =
          health_score
          + free_bonus
          + latency_bonus
        """
        health = health_reg.get(manifest.id)

        # Health component (0-100)
        score = health.score()

        # User priority: free providers get a small bonus
        if manifest.category == "free":
            score += 10

        # Latency: prefer lower latency
        if health.avg_latency_ms > 0:
            latency_bonus = max(0, 20 - health.avg_latency_ms / 200)
            score += latency_bonus

        return score
