"""
config/settings.py
配置管理：路径常量、默认配置、读写接口

v5 新增字段：
  together_key, gemini_key, openrouter_key, openrouter_model, xai_key
"""
import json
import os

# ─── 应用路径 ──────────────────────────────────────────────────
APP_DIR      = os.path.expanduser("~/.text_to_image_app")
IMAGES_DIR   = os.path.join(APP_DIR, "images")
DB_FILE      = os.path.join(APP_DIR, "history.db")
HISTORY_FILE = os.path.join(APP_DIR, "history.json")   # 旧版，仅用于迁移
CONFIG_FILE  = os.path.join(APP_DIR, "config.json")
LOG_FILE     = os.path.join(APP_DIR, "debug.log")

os.makedirs(APP_DIR, mode=0o700, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# ─── 默认配置 ──────────────────────────────────────────────────
DEFAULT_CONFIG: dict = {
    "config_version": 2,
    "language": "zh-CN",
    # ── 免费接口 ──────────────────────────────────────────────
    "sf_key":               "",   # 硅基流动 API Key
    "hf_token":             "",   # HuggingFace Token
    "stablehorde_key":      "",   # StableHorde Key（空=匿名）
    "segmind_key":          "",   # Segmind API Key（注册送 $5）
    "pollinations_enabled": True, # Pollinations.AI（无需 Key）
    # ── 免费接口（v3 新增）────────────────────────────────────
    "cf_account_id":        "",   # Cloudflare Account ID
    "cf_api_token":         "",   # Cloudflare API Token
    "modelslab_key":        "",   # ModelsLab API Key（免费 100次/天）
    # ── 免费接口（v5 新增）────────────────────────────────────
    "together_key":         "",   # Together AI（FLUX.1 Free 免费端点）
    "gemini_key":           "",   # Google Gemini API（免费 500次/天）
    "openrouter_key":       "",   # OpenRouter（部分模型免费）
    "openrouter_model":     "black-forest-labs/FLUX.1-schnell:free",
    # ── 付费接口 ──────────────────────────────────────────────
    "openai_key":           "",
    "stability_key":        "",
    "replicate_key":        "",
    # ── 付费接口（v5 新增）────────────────────────────────────
    "xai_key":              "",   # xAI Grok Imagine（注册送 $25）
    # ── 商业变现接口（v6 新增）───────────────────────────────
    "ideogram_key":         "",   # Ideogram v2（文字入图首选，免费25次/天）
    "fal_key":              "",   # fal.ai FLUX Ultra（4MP高清，最高写实质量）
    "recraft_key":          "",   # Recraft v3（设计/插画/品牌VI）
    "recraft_style":        "realistic_image",  # realistic_image | digital_illustration | vector_illustration
    # ── 付费模型偏好 ───────────────────────────────────────────
    "dalle_model":          "dall-e-3",
    "dalle_quality":        "standard",
    "stability_model":      "core",
    "replicate_model":      "flux-1.1-pro",
    # ── 通用设置 ───────────────────────────────────────────────
    "default_provider":     "自动（按优先级）",
    "default_size":         "1024x1024",
    "show_wizard_on_start": True,
    "theme": "dark",
    # ── 变体质量设置 ───────────────────────────────────────────
    # variant_quality: "standard"（速度优先）| "high"（质量优先）
    # high 模式：各接口使用更高步数/更好模型，耗时约增加 50~100%
    "variant_quality":      "high",
}


def load_config() -> dict:
    """从磁盘加载配置，缺失键用默认值补全。"""
    cfg = DEFAULT_CONFIG.copy()
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            saved_ver = saved.get("config_version", 1)
            if saved_ver < 2:
                saved = _migrate_config_v1_to_v2(saved)
            cfg.update(saved)
    except Exception:
        pass  # 配置加载失败，使用默认配置
    return cfg


def _migrate_config_v1_to_v2(cfg: dict) -> dict:
    """Migrate v1 config to v2 format."""
    cfg["config_version"] = 2
    # Future migrations go here
    return cfg


def save_config(cfg: dict) -> None:
    """将配置持久化到磁盘。"""
    os.makedirs(APP_DIR, mode=0o700, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.chmod(CONFIG_FILE, 0o600)
