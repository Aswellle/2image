"""
config/theme.py — Unified color scheme and design tokens.
All UI modules import from here for global color consistency.

本项目只提供暗色主题（DARK_THEME）。语义令牌（semantic names）
由 config/design_tokens.py 提供并从本模块的主题 dict 派生。
"""
from config.design_tokens import TOKENS, sync_tokens_from_theme



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
    "surface_disabled": "#334155",
    "text_disabled":   "#94a3b8",
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


# ─── Theme infrastructure（暗色单主题）────────────────────────
# 项目决定只保留暗色模式：无运行时切换，C 即 DARK_THEME 本体。

C = DARK_THEME


def init_theme(cfg: dict | None = None) -> None:
    """初始化令牌同步（保留入口以兼容既有调用方；cfg 兼容旧配置键）。"""
    sync_tokens_from_theme(TOKENS, DARK_THEME)


# 模块加载即完成令牌初始同步（TOKENS 从主题 dict 派生）
sync_tokens_from_theme(TOKENS, DARK_THEME)
