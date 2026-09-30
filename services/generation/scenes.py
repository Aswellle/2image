"""
services/generation/scenes.py — 场景路由语义（Phase 3 自 smart_router.py 迁入）
───────────────────────────────────────────────────────────────────────────────
商业场景 → 接口优先序列、模板 ID → 场景、关键词 → 场景的纯数据与纯函数，
供 services/generation/router.py 消费。此模块不含过滤/健康逻辑。
"""

# ── 场景 → 接口优先序列 ─────────────────────────────────────────
# Values must be stable provider_id (matching ALL_PROVIDERS keys)
ROUTES: dict = {
    # 文字入图：Banner、海报、标签、LOGO
    "text_overlay": [
        "ideogram",
        "openai_image",
        "siliconflow",
    ],
    # 高端写实摄影：产品图、人像、杂志封面
    "product_photo": [
        "fal_flux",
        "stability_ai",
        "siliconflow",
        "openai_image",
        "pollinations",
    ],
    # 设计/插画/品牌VI
    "illustration": [
        "recraft",
        "openai_image",
        "siliconflow",
        "gemini",
    ],
    # 电商主图（白底/场景）
    "ecommerce": [
        "fal_flux",
        "stability_ai",
        "siliconflow",
        "pollinations",
    ],
    # 社媒封面（小红书/公众号/短视频）
    "social_media": [
        "siliconflow",
        "fal_flux",
        "gemini",
        "pollinations",
    ],
    # 科技/品牌宣传
    "brand_tech": [
        "fal_flux",
        "openai_image",
        "siliconflow",
        "recraft",
    ],
}

# ── 模板ID → 商业场景 ─────────────────────────────────────────
TEMPLATE_SCENE: dict = {
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
KEYWORD_RULES: list = [
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


def scene_for_template(template_id: str) -> str:
    """模板 ID 最优先；无映射返回空串。"""
    return TEMPLATE_SCENE.get(template_id, "")


def detect_scene(prompt: str) -> str:
    """从提示词关键词推断商业场景，返回场景名或空字符串。"""
    prompt_lower = (prompt or "").lower()
    for keywords, scene in KEYWORD_RULES:
        if any(kw.lower() in prompt_lower for kw in keywords):
            return scene
    return ""


def route_for(scene: str) -> list:
    """场景对应路由；未知场景返回空列表。"""
    return list(ROUTES.get(scene, []))
