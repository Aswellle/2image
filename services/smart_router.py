"""
services/smart_router.py — 意图感知路由器
根据商业场景/模板ID/提示词关键词，返回最优接口优先序列。

使用方式：
    from services.smart_router import get_provider_order
    order = get_provider_order(prompt, cfg, template_id="xhs_hot")
    data, used = image_service.generate_image(prompt, w, h, seed, cfg,
                                              provider_order=order)
"""

# ── 场景 → 接口优先序列 ─────────────────────────────────────────
# 名称必须与 services/providers/__init__.py 中 ALL_PROVIDERS 的键完全一致
_ROUTES: dict = {
    # 文字入图：Banner、海报、标签、LOGO
    "text_overlay": [
        "Ideogram v2 (文字入图)",
        "💎 OpenAI DALL-E 3",
        "硅基流动 SiliconFlow (★推荐)",
    ],
    # 高端写实摄影：产品图、人像、杂志封面
    "product_photo": [
        "fal.ai FLUX Ultra (高质量)",
        "💎 Stability AI",
        "硅基流动 SiliconFlow (★推荐)",
        "💎 OpenAI DALL-E 3",
        "Pollinations.AI (免费·无需Key)",
    ],
    # 设计/插画/品牌VI
    "illustration": [
        "Recraft v3 (设计/插画)",
        "💎 OpenAI DALL-E 3",
        "硅基流动 SiliconFlow (★推荐)",
        "Google Gemini (免费500次/天)",
    ],
    # 电商主图（白底/场景）
    "ecommerce": [
        "fal.ai FLUX Ultra (高质量)",
        "💎 Stability AI",
        "硅基流动 SiliconFlow (★推荐)",
        "Pollinations.AI (免费·无需Key)",
    ],
    # 社媒封面（小红书/公众号/短视频）
    "social_media": [
        "硅基流动 SiliconFlow (★推荐)",
        "fal.ai FLUX Ultra (高质量)",
        "Google Gemini (免费500次/天)",
        "Pollinations.AI (免费·无需Key)",
    ],
    # 科技/品牌宣传
    "brand_tech": [
        "fal.ai FLUX Ultra (高质量)",
        "💎 OpenAI DALL-E 3",
        "硅基流动 SiliconFlow (★推荐)",
        "Recraft v3 (设计/插画)",
    ],
}

# ── 模板ID → 商业场景 ─────────────────────────────────────────
_TEMPLATE_SCENE: dict = {
    "xhs_hot":      "social_media",
    "xhs_travel":   "social_media",
    "xhs_food":     "ecommerce",
    "xhs_beauty":   "ecommerce",
    "xhs_outfit":   "social_media",

    "emotion_dramatic":   "product_photo",
    "emotion_healing":    "social_media",
    "emotion_aesthetic":  "product_photo",
    "emotion_motivation": "product_photo",

    "knowledge_clean":   "social_media",
    "knowledge_tech":    "brand_tech",
    "knowledge_finance": "social_media",
    "knowledge_health":  "social_media",

    "wechat_header":    "social_media",
    "wechat_square":    "social_media",
    "wechat_narrative": "social_media",
    "wechat_festive":   "illustration",
    "wechat_brand":     "brand_tech",

    "ecom_product":    "ecommerce",
    "ecom_lifestyle":  "ecommerce",
    "ecom_detail":     "ecommerce",
    "ecom_livestream": "social_media",

    "video_youtube": "social_media",
    "video_short":   "social_media",
    "video_podcast": "social_media",

    "art_concept":   "illustration",
    "art_portrait":  "illustration",
    "art_wallpaper": "product_photo",

    "brand_product_launch": "brand_tech",
    "brand_social_ad":      "ecommerce",
    "brand_infographic":    "brand_tech",
}

# ── 关键词 → 场景（按优先级排列，先匹配先生效）─────────────────
_KEYWORD_RULES: list = [
    (["文字", "字体", "标题", "banner", "Banner", "logo", "Logo",
      "海报", "标语", "slogan", "Slogan", "text", "typography",
      "label", "标签", "品牌名", "店招"], "text_overlay"),
    (["插画", "卡通", "矢量", "图标", "icon", "Icon",
      "illustration", "vector", "手绘", "flat design",
      "平面设计", "UI"], "illustration"),
    (["产品", "商品", "白底", "展示", "product", "白色背景",
      "平铺", "flat lay", "电商", "淘宝", "天猫",
      "主图", "详情页", "包装"], "ecommerce"),
    (["人像", "写真", "棚拍", "商业摄影", "portrait",
      "model", "模特", "硬照", "fashion", "Fashion"], "product_photo"),
    (["科技", "品牌", "发布", "宣传", "tech", "brand",
      "launch", "企业", "corporate"], "brand_tech"),
]

# ── 付费接口对应的 cfg Key ─────────────────────────────────────
_KEY_MAP: dict = {
    "Ideogram v2 (文字入图)":     "ideogram_key",
    "fal.ai FLUX Ultra (高质量)": "fal_key",
    "Recraft v3 (设计/插画)":     "recraft_key",
    "💎 OpenAI DALL-E 3":         "openai_key",
    "💎 Stability AI":             "stability_key",
    "💎 Replicate FLUX":           "replicate_key",
    "💎 xAI Grok Imagine":         "xai_key",
}

_FREE_PROVIDERS: set = {
    "硅基流动 SiliconFlow (★推荐)",
    "Google Gemini (免费500次/天)",
    "Pollinations.AI (免费·无需Key)",
    "Cloudflare AI (免费1万次/天)",
    "ModelsLab (免费100次/天)",
    "Segmind (注册送$5)",
    "OpenRouter (部分免费)",
    "HuggingFace (备用)",
    "StableHorde (兜底)",
}


def _filter_available(order: list, cfg: dict) -> list:
    """过滤掉未配置 Key 的付费接口，保留已配置的付费接口和所有免费接口。"""
    result = []
    for name in order:
        if name in _FREE_PROVIDERS:
            result.append(name)
        elif name in _KEY_MAP:
            if cfg.get(_KEY_MAP[name], "").strip():
                result.append(name)
    return result


def _detect_scene(prompt: str) -> str:
    """从提示词关键词推断商业场景，返回场景名或空字符串。"""
    prompt_lower = prompt.lower()
    for keywords, scene in _KEYWORD_RULES:
        if any(kw.lower() in prompt_lower for kw in keywords):
            return scene
    return ""


def get_provider_order(
    prompt: str,
    cfg: dict,
    template_id: str = "",
    fallback_order: list = None,
) -> list:
    """
    返回针对当前请求的最优接口优先序列。

    Parameters
    ----------
    prompt        : 用户提示词（用于关键词检测）
    cfg           : 配置字典（用于过滤未配置的付费接口）
    template_id   : 当前模板ID（优先于关键词检测）
    fallback_order: 兜底顺序，None 时使用 DEFAULT_ORDER

    Returns
    -------
    list[str]  有效接口名称列表，至少包含一个免费兜底接口
    """
    from services.providers import DEFAULT_ORDER as _DEFAULT

    # 1. 模板ID最优先
    scene = _TEMPLATE_SCENE.get(template_id, "")
    # 2. 关键词推断
    if not scene:
        scene = _detect_scene(prompt)

    if scene and scene in _ROUTES:
        order = list(_ROUTES[scene])
        # 把未在场景列表中的接口追加到末尾（保证完整兜底）
        existing = set(order)
        for name in (fallback_order or _DEFAULT):
            if name not in existing:
                order.append(name)
    else:
        order = list(fallback_order or _DEFAULT)

    available = _filter_available(order, cfg)

    # 保证最终列表非空
    if not available:
        available = ["Pollinations.AI (免费·无需Key)"]

    return available
