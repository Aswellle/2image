"""
config/model_catalog.py — 每族图像模型的「可选值 + 默认值」唯一来源

settings.DEFAULT_CONFIG 的默认值、provider 的兜底默认（cfg.get 的 fallback），
以及向导下拉（ui/wizard_free.py / ui/wizard_paid.py）的 values 列表均从这里引用，
避免同一模型清单散落多处后漂移——新增 / 改名模型只需改这一处。

注意：这是 config 层的纯常量模块，不得 import services/ui，防止依赖环。
"""
from __future__ import annotations

# ── OpenAI GPT-Image 家族（provider: services/providers/openai_image.py）──────
# gpt-image-1 系列仅支持预设尺寸；gpt-image-2+ 支持任意尺寸
GPT_IMAGE_1        = "gpt-image-1"
GPT_IMAGE_1_MINI   = "gpt-image-1-mini"
GPT_IMAGE_1_5      = "gpt-image-1.5"
GPT_IMAGE_2        = "gpt-image-2"
GPT_IMAGE_25_FLARE    = "gpt-image-2.5-flare"
GPT_IMAGE_25_SUNBURST = "gpt-image-2.5-sunburst"

GPT_IMAGE_MODELS = [
    GPT_IMAGE_1,
    GPT_IMAGE_1_MINI,
    GPT_IMAGE_1_5,
    GPT_IMAGE_2,
    GPT_IMAGE_25_FLARE,
    GPT_IMAGE_25_SUNBURST,
]
GPT_IMAGE_DEFAULT = GPT_IMAGE_2  # 默认使用最新稳定版

# 人类可读名称映射
GPT_IMAGE_NAMES: dict[str, str] = {
    GPT_IMAGE_1:           "GPT-Image 1 (旧版)",
    GPT_IMAGE_1_MINI:      "GPT-Image 1 Mini",
    GPT_IMAGE_1_5:         "GPT-Image 1.5",
    GPT_IMAGE_2:           "GPT-Image 2",
    GPT_IMAGE_25_FLARE:    "GPT-Image 2.5 Flare (快速)",
    GPT_IMAGE_25_SUNBURST: "GPT-Image 2.5 Sunburst (最强)",
}

# 标记为 Legacy 的模型（UI 显示旧版标签，默认不选中）
GPT_IMAGE_LEGACY = {GPT_IMAGE_1, GPT_IMAGE_1_MINI, GPT_IMAGE_1_5}

# ── Google Gemini 图像家族（provider: services/providers/gemini.py）──────────
# Nano Banana 系列：v1 已弃用，v2 为当前稳定版
GEMINI_NB_V1       = "gemini-2.5-flash-image"       # Nano Banana (v1, 即将下线)
GEMINI_NB_V2       = "gemini-3.1-flash-image"       # Nano Banana 2
GEMINI_NB_V2_LITE  = "gemini-3.1-flash-lite-image"  # Nano Banana 2 Lite
GEMINI_NB_PRO      = "gemini-3-pro-image"           # Nano Banana Pro

GEMINI_IMAGE_MODELS = [
    GEMINI_NB_V1,
    GEMINI_NB_V2,
    GEMINI_NB_V2_LITE,
    GEMINI_NB_PRO,
]
GEMINI_IMAGE_DEFAULT = GEMINI_NB_V2  # 默认使用 Nano Banana 2

# 人类可读名称映射
GEMINI_IMAGE_NAMES: dict[str, str] = {
    GEMINI_NB_V1:      "Nano Banana v1 (即将下线)",
    GEMINI_NB_V2:      "Nano Banana 2",
    GEMINI_NB_V2_LITE: "Nano Banana 2 Lite",
    GEMINI_NB_PRO:     "Nano Banana Pro",
}

# 标记为弃用的模型
GEMINI_IMAGE_DEPRECATED = {GEMINI_NB_V1}

# ── MiniMax 图像家族（provider: services/providers/minimax_image.py）─────────
MINIMAX_IMAGE_01 = "image-01"

MINIMAX_IMAGE_MODELS = [MINIMAX_IMAGE_01]
MINIMAX_IMAGE_DEFAULT = MINIMAX_IMAGE_01

MINIMAX_IMAGE_NAMES: dict[str, str] = {
    MINIMAX_IMAGE_01: "MiniMax Image 01",
}

# ── 火山引擎豆包（provider: services/providers/volcengine_ark.py）─────────────
ARK_SEEDREAM_30_T2I = "doubao-seedream-3-0-t2i"  # 豆包文生图 3.0
ARK_SEEDREAM_40_T2I = "doubao-seedream-4-0-t2i"  # 豆包文生图 4.0
ARK_SEEDIT_30_I2I   = "doubao-seededit-3-0-i2i"  # 豆包图生图 3.0

ARK_IMAGE_MODELS = [
    ARK_SEEDREAM_30_T2I,
    ARK_SEEDREAM_40_T2I,
    ARK_SEEDIT_30_I2I,
]
ARK_IMAGE_DEFAULT = ARK_SEEDREAM_40_T2I  # 默认使用最新最强

ARK_IMAGE_NAMES: dict[str, str] = {
    ARK_SEEDREAM_30_T2I: "豆包 Seedream 3.0 (文生图)",
    ARK_SEEDREAM_40_T2I: "豆包 Seedream 4.0 (文生图, 最新)",
    ARK_SEEDIT_30_I2I:   "豆包 SeedEdit 3.0 (图生图)",
}

# 图生图模型（用于 img2img 模式自动选择）
ARK_IMG2IMG_MODELS = {ARK_SEEDIT_30_I2I}

# ── Black Forest Labs 文生图模型（provider: services/providers/bfl_flux.py）───
# 图生图固定走 flux-kontext-pro（见 bfl_flux.py），不在此列。
BFL_TXT2IMG_MODELS = ["flux-pro-1.1", "flux-2-pro", "flux-2-flex"]
BFL_TXT2IMG_DEFAULT = BFL_TXT2IMG_MODELS[0]
