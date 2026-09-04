"""
config/model_catalog.py — 每族图像模型的「可选值 + 默认值」唯一来源

settings.DEFAULT_CONFIG 的默认值、provider 的兜底默认（cfg.get 的 fallback），
以及向导下拉（ui/wizard_free.py / ui/wizard_paid.py）的 values 列表均从这里引用，
避免同一模型清单散落多处后漂移——新增 / 改名模型只需改这一处。

注意：这是 config 层的纯常量模块，不得 import services/ui，防止依赖环。
"""
from __future__ import annotations

# ── OpenAI GPT-Image 家族（provider: services/providers/openai_image.py）──────
GPT_IMAGE_2 = "gpt-image-2"   # 唯一走「任意尺寸」路由的模型前缀
GPT_IMAGE_MODELS = ["gpt-image-1", "gpt-image-1-mini", GPT_IMAGE_2]
GPT_IMAGE_DEFAULT = GPT_IMAGE_MODELS[0]

# ── Google Gemini 图像家族（provider: services/providers/gemini.py）──────────
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-3.1-flash-image"]
GEMINI_IMAGE_DEFAULT = GEMINI_IMAGE_MODELS[0]

# ── Black Forest Labs 文生图模型（provider: services/providers/bfl_flux.py）───
# 图生图固定走 flux-kontext-pro（见 bfl_flux.py），不在此列。
BFL_TXT2IMG_MODELS = ["flux-pro-1.1", "flux-2-pro", "flux-2-flex"]
BFL_TXT2IMG_DEFAULT = BFL_TXT2IMG_MODELS[0]
