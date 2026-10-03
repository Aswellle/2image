"""
config/theme.py — Unified color scheme and design tokens.
All UI modules import from here for global color consistency.

Design tokens (semantic names) are provided via config/design_tokens.py
This module provides backward-compatible DARK_THEME/LIGHT_THEME dicts.
"""
from config.design_tokens import TOKENS, LIGHT_TOKENS, sync_tokens_from_theme



DARK_THEME = {
    # 基础
    "bg":       "#1a1a2e",
    "panel":    "#16213e",
    "acc":      "#0f3460",
    "hl":       "#e94560",
    "text":     "#eaeaea",
    "sub":      "#c0cfe0",
    "entry":    "#0d2847",
    "ok":       "#4ecca3",
    "warn":     "#f0a500",
    "sep":      "#2a3a5a",
    # 卡片 / 选中
    "card":     "#1e2d4a",
    "card_hl":  "#243a60",
    "card_sel": "#1a3a6a",
    "card_fav": "#1a2a1a",
    "empty":    "#0d1a2a",
    # 收藏 / 操作
    "star_on":  "#f59e0b",
    "star_off": "#4a5a7a",
    "keep_bg":  "#065f46",
    "dis_bg":   "#7f1d1d",
    "purple":   "#7c3aed",
    "dpurp":    "#6d28d9",
    "gold":     "#f59e0b",
    "paid":     "#7c3aed",
    # 分隔 / 对比
    "sash":     "#2a4a8a",
    "sash_hl":  "#4a7adf",
    "cmp_a":    "#1d4ed8",
    "cmp_b":    "#9f1239",
    "neg_fg":   "#f87171",
    "neg_bg":   "#2a1018",
    # 辅助
    "guide":    "#89b4fa",
    "tb":       "#0d1b2a",
    # ── 语义令牌别名（UIUX §34/§68：新代码用语义名，旧键保持兼容）──
    "surface":         "#1a1a2e",
    "surface_raised":  "#16213e",
    "surface_hover":   "#243a60",
    "surface_selected": "#1a3a6a",
    "accent":          "#0f3460",
    "accent_hover":    "#1a4a7f",
    "success":         "#4ecca3",
    "danger":          "#e94560",
    "warning":         "#f0a500",
    "divider":         "#2a3a5a",
    "text_primary":    "#eaeaea",
    "text_secondary":  "#c0cfe0",
    "text_muted":      "#8a9aba",
    "text_inverse":    "#ffffff",
}
LIGHT_THEME = {
    # 基础
    "bg":       "#f0f2f5",
    "panel":    "#ffffff",
    "acc":      "#1a56db",
    "hl":       "#dc2626",
    "text":     "#1a1a2e",
    "sub":      "#4a5568",
    "entry":    "#ffffff",
    "ok":       "#059669",
    "warn":     "#d97706",
    "sep":      "#e2e8f0",
    # 卡片 / 选中
    "card":     "#ffffff",
    "card_hl":  "#eff6ff",
    "card_sel": "#dbeafe",
    "card_fav": "#fefce8",
    "empty":    "#f8fafc",
    # 收藏 / 操作
    "star_on":  "#f59e0b",
    "star_off": "#cbd5e1",
    "keep_bg":  "#059669",
    "dis_bg":   "#dc2626",
    "purple":   "#7c3aed",
    "dpurp":    "#6d28d9",
    "gold":     "#f59e0b",
    "paid":     "#7c3aed",
    # 分隔 / 对比
    "sash":     "#94a3b8",
    "sash_hl":  "#3b82f6",
    "cmp_a":    "#1d4ed8",
    "cmp_b":    "#dc2626",
    "neg_fg":   "#dc2626",
    "neg_bg":   "#fef2f2",
    # 辅助
    "guide":    "#2563eb",
    "tb":       "#f1f5f9",
    # ── 语义令牌别名 ──
    "surface":         "#f0f2f5",
    "surface_raised":  "#ffffff",
    "surface_hover":   "#eff6ff",
    "surface_selected": "#dbeafe",
    "accent":          "#1a56db",
    "accent_hover":    "#3b82f6",
    "success":         "#059669",
    "danger":          "#dc2626",
    "warning":         "#d97706",
    "divider":         "#e2e8f0",
    "text_primary":    "#1a1a2e",
    "text_secondary":  "#4a5568",
    "text_muted":      "#718096",
    "text_inverse":    "#ffffff",
}

# ── 标签色彩 ──────────────────────────────────────────────────
TAG_PALETTE = [
    "#7c3aed", "#0f6460", "#92400e", "#1e40af",
    "#9f1239", "#065f46", "#0369a1", "#4a1d96",
]

def tag_color(tag: str) -> str:
    """确定性标签颜色（hash → palette）。使用 md5 避免字符顺序碰撞。"""
    import hashlib
    h = int(hashlib.md5(tag.encode()).hexdigest(), 16)
    return TAG_PALETTE[h % len(TAG_PALETTE)]


# ─── Theme switching infrastructure ──────────────────────────

_current_theme = "dark"

THEMES = {
    "dark":  DARK_THEME,
    "light": LIGHT_THEME,
}

# Active theme dict — for future runtime switching.
# Existing UI files import DARK_THEME as C directly; this global C
# is for new code that wants runtime theme switching.
C = DARK_THEME  # same object — mutations via apply_theme() are visible to all importers


def apply_theme(theme_name: str) -> None:
    """Switch to a named theme. Requires app restart for full effect."""
    global _current_theme, C
    if theme_name in THEMES:
        _current_theme = theme_name
        C.update(THEMES[theme_name])
        # 活动令牌跟随主题切换：原地同步，组件无需重建
        # （LIGHT_TOKENS 保持浅色常量语义，不随切换变动）
        sync_tokens_from_theme(TOKENS, THEMES[theme_name])


def get_theme() -> str:
    return _current_theme


def init_theme(cfg: dict) -> None:
    """Initialize theme from config on app startup."""
    theme_name = cfg.get("theme", "dark")
    apply_theme(theme_name)


# 模块加载即完成令牌初始同步（TOKENS/LIGHT_TOKENS 从主题 dict 派生）
sync_tokens_from_theme(TOKENS, DARK_THEME)
sync_tokens_from_theme(LIGHT_TOKENS, LIGHT_THEME)
