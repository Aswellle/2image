"""
services/generation/provider_manifest.py — Stable provider identity
───────────────────────────────────────────────────────────────────
Defines the manifest structure for providers with stable IDs
decoupled from display names.  The registry uses these IDs
for all routing decisions; display names are UI-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field



@dataclass(frozen=True)
class ProviderManifest:
    """Immutable provider identity — stable across renames."""

    id: str
    name: str  # Display name (UI only)
    category: str  # "free" | "paid" | "commercial"
    config_key: str | None = None
    description: str = ""
    supports_img2img: bool = False
    capabilities: set[str] = field(default_factory=lambda: {"text2image"})
    enabled_by_default: bool = True

    @property
    def needs_key(self) -> bool:
        return self.config_key is not None


# ─── Free Providers ───────────────────────────────────────────────

FREE_MANIFESTS: dict[str, ProviderManifest] = {
    "pollinations": ProviderManifest(
        id="pollinations",
        name="Pollinations.AI (免费·无需Key)",
        category="free",
        config_key=None,
        description="免费，无需 API Key",
    ),
    "siliconflow": ProviderManifest(
        id="siliconflow",
        name="硅基流动 SiliconFlow (★推荐)",
        category="free",
        config_key="sf_key",
        description="硅基流动，推荐",
    ),
    "gemini": ProviderManifest(
        id="gemini",
        name="Google Gemini Nano Banana (免费额度)",
        category="free",
        config_key="gemini_key",
        description="Google Gemini，免费额度",
        supports_img2img=True,
    ),
    "cloudflare_ai": ProviderManifest(
        id="cloudflare_ai",
        name="Cloudflare AI (免费1万次/天)",
        category="free",
        config_key="cf_api_token",
        description="Cloudflare AI Worker",
    ),
    "modelslab": ProviderManifest(
        id="modelslab",
        name="ModelsLab (免费100次/天)",
        category="free",
        config_key="modelslab_key",
        description="ModelsLab 免费额度",
    ),
    "segmind": ProviderManifest(
        id="segmind",
        name="Segmind (注册送$5)",
        category="free",
        config_key="segmind_key",
        description="Segmind 注册送 $5",
    ),
    "openrouter": ProviderManifest(
        id="openrouter",
        name="OpenRouter (统一 Image API)",
        category="free",
        config_key="openrouter_key",
        description="OpenRouter 统一接口",
    ),
    "huggingface": ProviderManifest(
        id="huggingface",
        name="HuggingFace (备用)",
        category="free",
        config_key="hf_token",
        description="HuggingFace 备用",
    ),
    "stablehorde": ProviderManifest(
        id="stablehorde",
        name="StableHorde (兜底)",
        category="free",
        config_key="stablehorde_key",
        description="StableHorde 兜底",
    ),
    "together_ai": ProviderManifest(
        id="together_ai",
        name="Together AI (FLUX Free·免费)",
        category="free",
        config_key="together_key",
        description="Together AI FLUX",
    ),
    "dashscope_qwen": ProviderManifest(
        id="dashscope_qwen",
        name="通义万相 Qwen-Image (阿里云免费额度)",
        category="free",
        config_key="dashscope_key",
        description="阿里云通义万相",
    ),
    "bria_ai": ProviderManifest(
        id="bria_ai",
        name="Bria AI Fibo (免费1000次)",
        category="free",
        config_key="bria_key",
        description="Bria AI 免费额度",
    ),
}

# ─── Paid Providers ──────────────────────────────────────────────

PAID_MANIFESTS: dict[str, ProviderManifest] = {
    "openai_image": ProviderManifest(
        id="openai_image",
        name="💎 OpenAI GPT-Image",
        category="paid",
        config_key="openai_key",
        description="OpenAI DALL-E / GPT-Image",
        supports_img2img=True,
        capabilities={"text2image", "img2img", "edit"},
    ),
    "stability_ai": ProviderManifest(
        id="stability_ai",
        name="💎 Stability AI",
        category="paid",
        config_key="stability_key",
        description="Stability AI Core",
        supports_img2img=True,
    ),
    "replicate_flux": ProviderManifest(
        id="replicate_flux",
        name="💎 Replicate FLUX",
        category="paid",
        config_key="replicate_key",
        description="Replicate FLUX",
    ),
    "xai_grok": ProviderManifest(
        id="xai_grok",
        name="💎 xAI Grok Imagine",
        category="paid",
        config_key="xai_key",
        description="xAI Grok Imagine",
    ),
    "bfl_flux": ProviderManifest(
        id="bfl_flux",
        name="💎 Black Forest Labs FLUX",
        category="paid",
        config_key="bfl_key",
        description="BFL FLUX 官方",
        supports_img2img=True,
        capabilities={"text2image", "img2img"},
    ),
    "gemini_nano_banana_pro": ProviderManifest(
        id="gemini_nano_banana_pro",
        name="💎 Nano Banana Pro (Gemini 3 Pro Image)",
        category="paid",
        config_key="gemini_key",
        description="Gemini 3 Pro Image",
        supports_img2img=True,
        capabilities={"text2image", "img2img"},
    ),
    "minimax_image": ProviderManifest(
        id="minimax_image",
        name="💎 MiniMax image-01",
        category="paid",
        config_key="minimax_key",
        description="MiniMax image-01",
        supports_img2img=True,
        capabilities={"text2image", "img2img"},
    ),
}

# ─── Commercial Providers ────────────────────────────────────────

COMMERCIAL_MANIFESTS: dict[str, ProviderManifest] = {
    "ideogram": ProviderManifest(
        id="ideogram",
        name="Ideogram v4 (文字入图)",
        category="commercial",
        config_key="ideogram_key",
        description="Ideogram v4 文字入图",
    ),
    "fal_flux": ProviderManifest(
        id="fal_flux",
        name="fal.ai FLUX Ultra (高质量)",
        category="commercial",
        config_key="fal_key",
        description="fal.ai FLUX Ultra",
        supports_img2img=True,
        capabilities={"text2image", "img2img"},
    ),
    "recraft": ProviderManifest(
        id="recraft",
        name="Recraft v3/v4 (设计/插画)",
        category="commercial",
        config_key="recraft_key",
        description="Recraft 设计/插画",
    ),
}

ALL_MANIFESTS: dict[str, ProviderManifest] = {
    **FREE_MANIFESTS,
    **PAID_MANIFESTS,
    **COMMERCIAL_MANIFESTS,
}

# ─── Legacy Aliases ──────────────────────────────────────────────

LEGACY_NAME_TO_ID: dict[str, str] = {
    "Bria AI Fibo (免费1000次)": "bria_ai",
    "Cloudflare AI (免费1万次/天)": "cloudflare_ai",
    "通义万相 Qwen-Image (阿里云免费额度)": "dashscope_qwen",
    "Google Gemini Nano Banana (免费额度)": "gemini",
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

# ─── Free Provider Order (explicit, not pkgutil-dependent) ───────

FREE_PROVIDER_ORDER: list[str] = [
    "pollinations",
    "siliconflow",
    "gemini",
    "cloudflare_ai",
    "modelslab",
    "segmind",
    "openrouter",
    "huggingface",
    "stablehorde",
    "together_ai",
    "dashscope_qwen",
    "bria_ai",
]


def resolve_provider_id(name_or_id: str) -> str | None:
    """Convert a legacy display name or ID to a stable ID."""
    if name_or_id in ALL_MANIFESTS:
        return name_or_id
    return LEGACY_NAME_TO_ID.get(name_or_id)


def get_manifest(provider_id: str) -> ProviderManifest | None:
    return ALL_MANIFESTS.get(provider_id)
