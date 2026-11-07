"""
config/model_catalog.py — 每族图像模型的「可选值 + 默认值」唯一来源

settings.DEFAULT_CONFIG 的默认值、provider 的兜底默认（cfg.get 的 fallback），
以及向导下拉（ui/wizard_free.py / ui/wizard_paid.py）的 values 列表均从这里引用，
避免同一模型清单散落多处后漂移——新增 / 改名模型只需改这一处。

模型状态以 2026-11 各家官方文档/模型表核实为准：
  · OpenAI deprecations 页（gpt-image-1 已于 2026-10-23 关停，
    1-mini / 1.5 将于 2026-12-01 移除，2.6 系 2026-11-04 发布）
  · Gemini API deprecations 页（nano-banana-2.1 为官方推荐主力，
    2.5-flash-image 存活至 2027-03-15）
  · 火山方舟模型表（Seedream 正式 ID 带日期快照，"-t2i" 后缀仅 3.0 时代有效）
  · docs.bfl.ml 索引（FLUX.2 [pro] 为官方推荐默认，单端点生成+编辑）
  · docs.x.ai 模型页（grok-imagine-image-quality 已不在册）
  · 阿里云百炼文生图 V2 API（wan2.5 及以下走旧异步协议）

注意：这是 config 层的纯常量模块，不得 import services/ui，防止依赖环。
"""

from __future__ import annotations

# ── OpenAI GPT-Image 家族（provider: services/providers/openai_image.py）──────
# gpt-image-2 支持任意尺寸（16 的倍数，长边 ≤3840）；2.5/2.6 为特化变体。
# gpt-image-1（2026-10-23 关停）、gpt-image-1-mini / 1.5（2026-12-01 移除）
# 已从目录移除，存量配置值由 provider 归一化到默认。
GPT_IMAGE_2 = "gpt-image-2"
GPT_IMAGE_25_FLARE = "gpt-image-2.5-flare"
GPT_IMAGE_25_SUNBURST = "gpt-image-2.5-sunburst"
GPT_IMAGE_26_FLARE = "gpt-image-2.6-flare"
GPT_IMAGE_26_SUNBURST = "gpt-image-2.6-sunburst"

GPT_IMAGE_MODELS = [
    GPT_IMAGE_2,
    GPT_IMAGE_25_FLARE,
    GPT_IMAGE_25_SUNBURST,
    GPT_IMAGE_26_FLARE,
    GPT_IMAGE_26_SUNBURST,
]
GPT_IMAGE_DEFAULT = GPT_IMAGE_2  # 平衡款稳定默认；2.5/2.6 为特化变体

# 人类可读名称映射
GPT_IMAGE_NAMES: dict[str, str] = {
    GPT_IMAGE_2: "GPT-Image 2",
    GPT_IMAGE_25_FLARE: "GPT-Image 2.5 Flare (快速)",
    GPT_IMAGE_25_SUNBURST: "GPT-Image 2.5 Sunburst (最强)",
    GPT_IMAGE_26_FLARE: "GPT-Image 2.6 Flare (极速)",
    GPT_IMAGE_26_SUNBURST: "GPT-Image 2.6 Sunburst (最强·新)",
}

# ── Google Gemini 图像家族（provider: services/providers/gemini.py）──────────
# nano-banana-2.1 为官方推荐主力（2026-10-06 发布）；
# 2.5-flash-image 为 legacy（官方公告 2027-03-15 关停）。
GEMINI_NB_21 = "gemini-nano-banana-2.1"  # Nano Banana 2.1（推荐主力）
GEMINI_NB_V2 = "gemini-3.1-flash-image"  # Nano Banana 2（上一代主力）
GEMINI_NB_V2_LITE = "gemini-3.1-flash-lite-image"  # Nano Banana 2 Lite（轻量快速）
GEMINI_NB_PRO = "gemini-3-pro-image"  # Nano Banana Pro（最强画质）
GEMINI_NB_V1 = "gemini-2.5-flash-image"  # Nano Banana v1（legacy，2027-03-15 下线）

GEMINI_IMAGE_MODELS = [
    GEMINI_NB_21,
    GEMINI_NB_V2,
    GEMINI_NB_V2_LITE,
    GEMINI_NB_PRO,
    GEMINI_NB_V1,
]
GEMINI_IMAGE_DEFAULT = GEMINI_NB_21

# 人类可读名称映射
GEMINI_IMAGE_NAMES: dict[str, str] = {
    GEMINI_NB_21: "Nano Banana 2.1 (推荐)",
    GEMINI_NB_V2: "Nano Banana 2 (上一代)",
    GEMINI_NB_V2_LITE: "Nano Banana 2 Lite (轻量)",
    GEMINI_NB_PRO: "Nano Banana Pro (最强)",
    GEMINI_NB_V1: "Nano Banana v1 (2027-03 下线)",
}

# 标记为弃用/即将下线的模型（UI 显示旧版标签）
GEMINI_IMAGE_DEPRECATED = {GEMINI_NB_V1}

# ── MiniMax 图像家族（provider: services/providers/minimax_image.py）─────────
# 官方模型表当前仅 image-01；无 image-02。
MINIMAX_IMAGE_01 = "image-01"

MINIMAX_IMAGE_MODELS = [MINIMAX_IMAGE_01]
MINIMAX_IMAGE_DEFAULT = MINIMAX_IMAGE_01

MINIMAX_IMAGE_NAMES: dict[str, str] = {
    MINIMAX_IMAGE_01: "MiniMax Image 01",
}

# ── 火山引擎豆包（provider: services/providers/volcengine_ark.py）─────────────
# 正式模型 ID 为带日期快照（方舟文档示例同款）；"-t2i" 后缀仅 3.0 时代有效，
# 4.0 起若再使用会报「模型不存在」。
# Seedream 4.x 原生支持 image 参考图编辑（1–14 张），SeedEdit 3.0 仅作旧版兜底。
ARK_SEEDREAM_30_T2I = "doubao-seedream-3-0-t2i"  # 豆包文生图 3.0（legacy）
ARK_SEEDREAM_40_T2I = "doubao-seedream-4-0-250828"  # 豆包文生图 4.0（正式快照 ID）
ARK_SEEDREAM_45_T2I = "doubao-seedream-4-5-251128"  # 豆包 Seedream 4.5（综合最佳）
ARK_SEEDIT_30_I2I = "doubao-seededit-3-0-i2i"  # 豆包图生图 3.0（Seedream 4.x 原生编辑前的旧通道）

ARK_IMAGE_MODELS = [
    ARK_SEEDREAM_45_T2I,
    ARK_SEEDREAM_40_T2I,
    ARK_SEEDREAM_30_T2I,
    ARK_SEEDIT_30_I2I,
]
ARK_IMAGE_DEFAULT = ARK_SEEDREAM_45_T2I  # 默认最新综合最佳

ARK_IMAGE_NAMES: dict[str, str] = {
    ARK_SEEDREAM_45_T2I: "豆包 Seedream 4.5 (推荐)",
    ARK_SEEDREAM_40_T2I: "豆包 Seedream 4.0",
    ARK_SEEDREAM_30_T2I: "豆包 Seedream 3.0 (旧版)",
    ARK_SEEDIT_30_I2I: "豆包 SeedEdit 3.0 (图生图)",
}

# 原生支持参考图编辑（image 参数）的模型；不在表内的文生图模型
# 走图生图时回退 SeedEdit 3.0。
ARK_NATIVE_I2I_MODELS = {ARK_SEEDREAM_45_T2I, ARK_SEEDREAM_40_T2I}

# ── Black Forest Labs 文生图模型（provider: services/providers/bfl_flux.py）───
# FLUX.2 [pro] 为官方推荐默认（/v1/flux-2-pro 单端点生成+编辑，
# input_image×8）；flux-pro-1.1 为 FLUX 1.x legacy。
BFL_FLUX2_PRO = "flux-2-pro"
BFL_FLUX2_PRO_PREVIEW = "flux-2-pro-preview"
BFL_FLUX2_MAX = "flux-2-max"
BFL_FLUX2_FLEX = "flux-2-flex"
BFL_FLUX_PRO_11 = "flux-pro-1.1"

BFL_TXT2IMG_MODELS = [
    BFL_FLUX2_PRO,
    BFL_FLUX2_PRO_PREVIEW,
    BFL_FLUX2_MAX,
    BFL_FLUX2_FLEX,
    BFL_FLUX_PRO_11,
]
BFL_TXT2IMG_DEFAULT = BFL_FLUX2_PRO

BFL_IMAGE_NAMES: dict[str, str] = {
    BFL_FLUX2_PRO: "FLUX.2 Pro (推荐)",
    BFL_FLUX2_PRO_PREVIEW: "FLUX.2 Pro Preview",
    BFL_FLUX2_MAX: "FLUX.2 Max (最高画质)",
    BFL_FLUX2_FLEX: "FLUX.2 Flex (排版)",
    BFL_FLUX_PRO_11: "FLUX 1.1 Pro (旧版)",
}

# ── xAI Grok Imagine（provider: services/providers/xai_grok.py）──────────────
# 官方模型页仅列 grok-imagine-image-2.0（推荐，支持 quality 参数）与
# grok-imagine-image；grok-imagine-image-quality 已不在册。
XAI_IMAGE_2 = "grok-imagine-image-2.0"
XAI_IMAGE_1 = "grok-imagine-image"

XAI_IMAGE_MODELS = [XAI_IMAGE_2, XAI_IMAGE_1]
XAI_IMAGE_DEFAULT = XAI_IMAGE_2

XAI_IMAGE_NAMES: dict[str, str] = {
    XAI_IMAGE_2: "Grok Imagine 2.0 (推荐)",
    XAI_IMAGE_1: "Grok Imagine",
}

# ── 阿里云百炼 通义万相（provider: services/providers/dashscope_qwen.py）──────
# wan2.5 及以下走旧异步协议（与现有实现兼容）；wan2.6 仅新协议
# （maas 域名 + workspace 子域），接入需另行改造。
# wanx2.1 系列已列入阿里云「停止新购及服务下线」公告，保留为 legacy。
DASHSCOPE_WAN25 = "wan2.5-t2i"
DASHSCOPE_WAN21_TURBO = "wanx2.1-t2i-turbo"
DASHSCOPE_WAN21_PLUS = "wanx2.1-t2i-plus"

DASHSCOPE_MODELS = [
    DASHSCOPE_WAN25,
    DASHSCOPE_WAN21_TURBO,
    DASHSCOPE_WAN21_PLUS,
]
DASHSCOPE_DEFAULT = DASHSCOPE_WAN25

DASHSCOPE_NAMES: dict[str, str] = {
    DASHSCOPE_WAN25: "通义万相 2.5 (推荐)",
    DASHSCOPE_WAN21_TURBO: "万相 2.1 Turbo (旧版)",
    DASHSCOPE_WAN21_PLUS: "万相 2.1 Plus (旧版)",
}
