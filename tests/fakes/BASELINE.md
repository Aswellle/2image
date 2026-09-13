# Phase 0 Baseline — Config Schema v2.1.0
# Generated: 2026-09-14
# This documents the existing config structure for migration safety.

CONFIG_SCHEMA_VERSION = 2

# Current default config keys (from config/settings.py DEFAULT_CONFIG)
DEFAULT_CONFIG_KEYS = [
    "config_version",
    "language",
    "sf_key",
    "hf_token",
    "stablehorde_key",
    "segmind_key",
    "pollinations_enabled",
    "pollinations_key",
    "cf_account_id",
    "cf_api_token",
    "modelslab_key",
    "together_key",
    "gemini_key",
    "openrouter_key",
    "openrouter_model",
    "openai_key",
    "stability_key",
    "replicate_key",
    "xai_key",
    "ideogram_key",
    "fal_key",
    "recraft_key",
    "recraft_style",
    "recraft_model",
    "dashscope_key",
    "minimax_key",
    "bfl_key",
    "bria_key",
    "prompt_llm_preset",
    "deepseek_key",
    "gpt_image_model",
    "gpt_image_quality",
    "stability_model",
    "replicate_model",
    "gemini_model",
    "bfl_model",
    "default_provider",
    "default_size",
    "show_wizard_on_start",
    "theme",
    "variant_quality",
]

# Legacy provider display names → will need stable IDs in Phase 3
LEGACY_PROVIDER_ALIASES = {
    "Bria AI Fibo (免费1000次)": "bria_ai",
    "Cloudflare AI (免费1万次/天)": "cloudflare_ai",
    "通义万相 Qwen-Image (阿里云免费额度)": "dashscope_qwen",
    "Google Gemini Nano Banana (免费额度)": "gemini_nano_banana",
    "HuggingFace (备用)": "huggingface",
    "ModelsLab (免费100次/天)": "modelslab",
    "OpenRouter (统一 Image API)": "openrouter",
    "Pollinations.AI (免费·无需Key)": "pollinations",
    "Segmind (注册送$5)": "segmind",
    "硅基流动 SiliconFlow (★推荐)": "siliconflow",
    "StableHorde (兜底)": "stablehorde",
    "Together AI (FLUX Free·免费)": "together_ai",
    "💎 Black Forest Labs FLUX": "bfl_flux",
    "💎 Nano Banana Pro (Gemini 3 Pro Image)": "gemini_nano_banana_pro",
    "💎 MiniMax image-01": "minimax_image",
    "💎 OpenAI GPT-Image": "openai_image",
    "💎 Replicate FLUX": "replicate_flux",
    "💎 Stability AI": "stability_ai",
    "💎 xAI Grok Imagine": "xai_grok",
    "fal.ai FLUX Ultra (高质量)": "fal_flux",
    "Ideogram v4 (文字入图)": "ideogram",
    "Recraft v3/v4 (设计/插画)": "recraft",
}

# Test baseline: 109 tests pass at v2.1.0
# Coverage fail-under: 30% (will raise to 70% in Phase 7)
