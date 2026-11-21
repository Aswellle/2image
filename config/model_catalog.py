"""
config/model_catalog.py — 每族图像模型的「可选值 + 默认值」唯一来源

settings.DEFAULT_CONFIG 的默认值、provider 的兜底默认（cfg.get 的 fallback），
以及向导下拉（ui/wizard_free.py / ui/wizard_paid.py）的 values 列表均从这里引用，
避免同一模型清单散落多处后漂移——新增 / 改名模型只需改这一处。

治理边界（与 tests/test_model_catalog_consistency.py 的锁定范围一致）：
  · 跨 provider 的模型族（OpenAI/Gemini/MiniMax/Ark/BFL/xAI/万相/Recraft）
    全部收录于此；recraft/replicate 等单 provider 自有族中，Replicate 的
    模型清单留在其 provider 模块（_MODELS/MODEL_ORDER）——因为它的每个
    模型各有一套请求 schema（_build_input），schema 知识与清单必须同居，
    一致性测试从 provider 侧桥接锁定。
  · 显示名为 zh-CN 单语策略：括注（推荐/极速/旧版）直接服务主受众，
    不经 i18n（config 层禁止 import ui/i18n）。
  · 快照型 ID（如 Ark 的 doubao-seedream-4-5-251128）由官方轮替，
    退役时需发版更新目录——这是接受已知维护成本的有意选择，不是遗漏。

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
# 2026-11-22 校准：H3-Image（2026-11-11 发布，文生图+编辑，最高
# 20MP）已上架 MiniMax 官方 API 平台；image-01 退役。
MINIMAX_H3_IMAGE = "MiniMax-H3-Image"
MINIMAX_H3_HS = "MiniMax-H3-Image-Highspeed"

MINIMAX_IMAGE_MODELS = [MINIMAX_H3_IMAGE, MINIMAX_H3_HS]
MINIMAX_IMAGE_DEFAULT = MINIMAX_H3_IMAGE

MINIMAX_IMAGE_NAMES: dict[str, str] = {
    MINIMAX_H3_IMAGE: "MiniMax H3 Image (推荐)",
    MINIMAX_H3_HS: "MiniMax H3 Image Highspeed (更快)",
}

# ── 火山引擎豆包（provider: services/providers/volcengine_ark.py）─────────────
# 正式模型 ID 为带日期快照（方舟文档示例同款）；"-t2i" 后缀仅 3.0 时代有效，
# 4.0 起若再使用会报「模型不存在」。
# Seedream 5.x 原生支持 image 参考图编辑（5.5 官方支持最多 10 张参考图与
# 多轮精准编辑）；旧 SeedEdit 3.0 通道随 4.x 一起退役。
# 2026-11-22 校准：5.5（2026-11-09 发布）为默认；4.5/4.0/3.0 已落后 1-3 代，
# 从目录移除——存量配置中的旧 ID 由 provider 自动归一化到新默认。
ARK_SEEDREAM_55_T2I = "doubao-seedream-5-5-261028"  # 豆包 Seedream 5.5（最新，多轮精准编辑/原生 RGBA）
ARK_SEEDREAM_50_PRO = "doubao-seedream-5-0-pro-260628"  # 豆包 Seedream 5.0 Pro（上一代旗舰）
ARK_SEEDREAM_50_FLASH = "doubao-seedream-5-0-flash-260915"  # 豆包 Seedream 5.0 Flash（同能力更快更省）

ARK_IMAGE_MODELS = [
    ARK_SEEDREAM_55_T2I,
    ARK_SEEDREAM_50_PRO,
    ARK_SEEDREAM_50_FLASH,
]
ARK_IMAGE_DEFAULT = ARK_SEEDREAM_55_T2I  # 默认最新发布

ARK_IMAGE_NAMES: dict[str, str] = {
    ARK_SEEDREAM_55_T2I: "豆包 Seedream 5.5 (推荐)",
    ARK_SEEDREAM_50_PRO: "豆包 Seedream 5.0 Pro",
    ARK_SEEDREAM_50_FLASH: "豆包 Seedream 5.0 Flash (更快更省)",
}

# 原生支持参考图编辑（image 参数）的模型——5.x 全系支持
ARK_NATIVE_I2I_MODELS = {ARK_SEEDREAM_55_T2I, ARK_SEEDREAM_50_PRO, ARK_SEEDREAM_50_FLASH}

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
# 2026-11-22 校准：wan2.6-t2i 已上线（官方推荐纯文生图优先，支持
# 同步/异步调用），为默认；wan2.5 走旧异步协议作次要档；wan2.1 系已
# 列入阿里云「停止新购及服务下线」公告，退役——存量配置归一化到默认。
# （maas 域名 + workspace 子域），接入需另行改造。
# wanx2.1 系列已列入阿里云「停止新购及服务下线」公告，保留为 legacy。
DASHSCOPE_WAN26 = "wan2.6-t2i"  # 万相 2.6 文生图（同步协议，官方推荐）
DASHSCOPE_WAN25 = "wan2.5-t2i"  # 万相 2.5（旧异步协议，紧邻次要）

DASHSCOPE_MODELS = [
    DASHSCOPE_WAN26,
    DASHSCOPE_WAN25,
]
DASHSCOPE_DEFAULT = DASHSCOPE_WAN26

DASHSCOPE_NAMES: dict[str, str] = {
    DASHSCOPE_WAN26: "通义万相 2.6 (推荐)",
    DASHSCOPE_WAN25: "通义万相 2.5 (旧异步协议)",
}

# ── Recraft（provider: services/providers/recraft.py）────────────────────────
# 官方 API 默认即 recraftv4_1（V4.1 2026-02-17 GA、05-14 迭代）；
# v3 未弃用，但 inpainting/outpainting/replace-background 等编辑操作
# 仍要求 v3（本 provider 仅文生图，不受影响）。
RECRAFT_V41 = "recraftv4_1"
RECRAFT_V3 = "recraftv3"

RECRAFT_MODELS = [RECRAFT_V41, RECRAFT_V3]
RECRAFT_DEFAULT = RECRAFT_V41

RECRAFT_IMAGE_NAMES: dict[str, str] = {
    RECRAFT_V41: "Recraft V4.1 (推荐)",
    RECRAFT_V3: "Recraft V3 (旧版)",
}
