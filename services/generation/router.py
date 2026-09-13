"""
services/generation/router.py — Health-aware scoring router v2
────────────────────────────────────────────────────────────────
Replaces smart_router.py with a scoring-based router that
considers: capability, health, latency, cost, quota, and user
priority — not just static keyword matching.
"""
from __future__ import annotations

import logging


from services.generation.provider_health import get_health_registry
from services.generation.provider_manifest import (
    ALL_MANIFESTS,
    COMMERCIAL_MANIFESTS,
    FREE_MANIFESTS,
    PAID_MANIFESTS,
    ProviderManifest,
    resolve_provider_id,
)

log = logging.getLogger(__name__)


class Router:
    """
    Score-based provider router.

    Usage::

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

        # Key check
        if manifest.config_key and not self.cfg.get(manifest.config_key):
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
          health_score * 30
          + user_priority * 25
          + latency_score * 15
          + free_bonus
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


def get_provider_order(
    prompt: str = "",
    cfg: dict | None = None,
    prefer_paid: bool = False,
    require_img2img: bool = False,
    explicit_provider: str | None = None,
) -> list[str]:
    """Convenience function matching the old smart_router interface."""
    router = Router(cfg or {})
    return router.get_order(
        prompt=prompt,
        prefer_paid=prefer_paid,
        require_img2img=require_img2img,
        explicit_provider=explicit_provider,
    )
