"""
services/smart_router.py — 兼容层（Phase 3 完成）
─────────────────────────────────────────────────
路由实现已迁移至 services/generation/router.py（健康感知 v3），
场景语义迁至 services/generation/scenes.py。
本文件仅保留旧导入路径的向后兼容；生产代码请直接使用：

    from services.generation.router import get_provider_order
"""
from services.generation.scenes import (  # noqa: F401
    KEYWORD_RULES as _KEYWORD_RULES,
    ROUTES as _ROUTES,
    TEMPLATE_SCENE as _TEMPLATE_SCENE,
    detect_scene as _detect_scene,
)
from services.generation.router import (  # noqa: F401
    _filter_available,
    get_provider_order,
)
