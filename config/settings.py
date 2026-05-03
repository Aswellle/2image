"""
config/settings.py
配置管理：路径常量、默认配置、读写接口

所有新增 Provider 的 API Key 均在此处声明默认值。
"""
import json
import os

# ─── 应用路径 ──────────────────────────────────────────────────
APP_DIR      = os.path.expanduser("~/.2image_app")
IMAGES_DIR   = os.path.join(APP_DIR, "images")
DB_FILE      = os.path.join(APP_DIR, "history.db")
HISTORY_FILE = os.path.join(APP_DIR, "history.json")   # 旧版，仅用于迁移
CONFIG_FILE  = os.path.join(APP_DIR, "config.json")
LOG_FILE     = os.path.join(APP_DIR, "debug.log")

os.makedirs(IMAGES_DIR, exist_ok=True)

# ─── 默认配置 ──────────────────────────────────────────────────
DEFAULT_CONFIG: dict = {
    # ── 免费接口（强烈推荐优先配置）──────────────────────────────
    "gemini_key":             "",   # Google Gemini API（免费 500次/天，aistudio.google.com）
    "pollinations_enabled":    True, # Pollinations.AI（无需 Key，直接可用）
    "cf_account_id":          "",   # Cloudflare Account ID（免费 1万次/天）
    "cf_api_token":           "",   # Cloudflare API Token
    "modelslab_key":          "",   # ModelsLab（免费 100次/天，支持 img2img）
    "siliconflow_key":        "",   # 硅基流动（FLUX.1-pro，低价稳定）
    "together_key":           "",   # Together AI（FLUX.1 Free 免费端点）
    "openrouter_key":         "",   # OpenRouter（聚合 16+ 模型，部分免费）
    "hf_token":               "",   # HuggingFace Token（备用）
    "stablehorde_key":        "",   # StableHorde Key（空=匿名）
    "segmind_key":            "",   # Segmind（注册送 $5，支持 img2img）

    # ── 付费接口 ────────────────────────────────────────────────
    "openai_key":             "",   # OpenAI DALL-E 3
    "stability_key":          "",   # Stability AI（支持 img2img）
    "replicate_key":          "",   # Replicate（FLUX.1 Pro）
    "xai_key":                "",   # xAI Grok（注册送 $25，$0.07/张）
    "ideogram_key":           "",   # Ideogram V2（注册送 100 次，文字图天花板）
    "recraft_key":            "",   # Recraft V3（50 次/小时免费）
    "leonardo_key":           "",   # Leonardo.ai（$10/月，150 tokens/天）

    # ── 提示词优化 ──────────────────────────────────────────────
    "deepseek_key":           "",   # DeepSeek V3（用于提示词扩写，非图片生成）

    # ── 模型偏好 ────────────────────────────────────────────────
    "dalle_model":             "dall-e-3",
    "dalle_quality":          "standard",
    "stability_model":        "core",
    "replicate_model":        "flux-1.1-pro",
    "openrouter_model":       "black-forest-labs/FLUX.1-schnell:free",
    "gemini_model":           "gemini-2.5-flash-preview-04-17",

    # ── 通用设置 ────────────────────────────────────────────────
    "default_provider":        "自动（按优先级）",
    "default_size":           "1024x1024",
    "show_wizard_on_start":   True,
    "variant_quality":        "high",
    "language":               "zh_CN",   # UI 语言：zh_CN / en_US
}


def load_config() -> dict:
    """从磁盘加载配置，缺失键用默认值补全。"""
    cfg = DEFAULT_CONFIG.copy()
    try:
        if os.path.exists(CONFIG_FILE):
            saved = json.load(open(CONFIG_FILE, "r", encoding="utf-8"))
            cfg.update(saved)
    except Exception:
        pass
    return cfg


def save_config(cfg: dict) -> None:
    """将配置持久化到磁盘。"""
    json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
