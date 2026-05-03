"""
services/providers/__init__.py
Provider 注册表 v1.0

每个 Provider 函数签名：
  try_xxx(prompt, w, h, seed, cfg, log) -> (bytes, str)
图生图（img2img）签名：
  try_xxx_img2img(prompt, w, h, seed, source_img_bytes, cfg, log) -> (bytes, str)
"""
from services.providers.pollinations    import try_pollinations
from services.providers.gemini          import try_gemini
from services.providers.cloudflare_ai   import try_cloudflare_ai
from services.providers.modelslab       import try_modelslab
from services.providers.siliconflow     import try_siliconflow
from services.providers.together_ai     import try_together_ai
from services.providers.openrouter      import try_openrouter
from services.providers.huggingface     import try_hf_inference
from services.providers.stablehorde     import try_stablehorde
from services.providers.segmind         import try_segmind
from services.providers.openai_dalle    import try_openai_dalle
from services.providers.stability_ai     import try_stability_ai
from services.providers.replicate_flux   import try_replicate
from services.providers.xai_grok        import try_xai_grok
from services.providers.ideogram        import try_ideogram
from services.providers.recraft         import try_recraft
from services.providers.leonardoai      import try_leonardo

FREE_PROVIDERS = {
    # 免费 / 近乎免费（无需 Key 或免费额度充足）
    "Google Gemini 2.5 Flash (免费500次/天)": try_gemini,
    "Google Gemini 3.1 Flash (低价高质量)":  None,  # TODO: 待接入
    "Pollinations.AI (免费·无需Key·支持img2img)": try_pollinations,
    "Cloudflare AI (免费1万次/天·SDXL)":     try_cloudflare_ai,
    "ModelsLab (免费100次/天·支持img2img)":  try_modelslab,
    "Segmind (注册送$5·支持img2img)":         try_segmind,
    "Together AI FLUX Free (免费限速)":       try_together_ai,
    "OpenRouter (聚合16+模型·部分免费)":      try_openrouter,
    "HuggingFace (备用)":                    try_hf_inference,
    "StableHorde (兜底)":                    try_stablehorde,
    # 高质量免费额度
    "Ideogram V2 (注册送100次·文字图天花板)": try_ideogram,
    "Recraft V3 (50次/小时·矢量/真实风格)":   try_recraft,
}

PAID_PROVIDERS = {
    # 付费优质
    "OpenAI DALL-E 3 (行业标杆)":            try_openai_dalle,
    "Stability AI SDXL (支持img2img)":       try_stability_ai,
    "Replicate FLUX.1 Pro":                  try_replicate,
    "xAI Grok Aurora (注册送$25·$0.07/张)": try_xai_grok,
    "Leonardo.ai ($10/月·150tokens/天)":      try_leonardo,
    # 低价高质
    "硅基流动 SiliconFlow (低价·国内可访问)": try_siliconflow,
}

ALL_PROVIDERS = {**FREE_PROVIDERS, **PAID_PROVIDERS}
DEFAULT_ORDER = list(FREE_PROVIDERS.keys())
