"""
services/prompt_assistant.py  v4
──────────────────────────────────────────────────────────────
AI 提示词助手后端服务：支持全维度参数 + 自媒体模板两种模式。

v4 核心优化：Token 预算控制 + 写实人像专项优化
════════════════════════════════════════════════════════════════

【根本问题分析】
  硅基流动 / HuggingFace 上的文生图模型均有 CLIP token 硬限制：
    · SDXL / SDXL-Lightning / SDXL-Turbo  → 77 token ≈ 55-60 词
    · SD 2.1 / SD 1.5                      → 77 token ≈ 55-60 词
    · FLUX.1-schnell（T5-XXL 侧）          → 256 token（但 >100 词后
      注意力被稀释，主体细节反而变弱）
  超出 77 token 的内容在 SDXL/SD 中被"硬截断"（完全丢弃，不是降权）。
  DeepSeek V3 指令遵循能力强但容易生成 150-200 词的长提示词，
  导致关键细节被截断，写实感降低。

【最优平衡策略】
  目标词数：58-72 英文单词（约 380-480 字符）
  · SDXL/SD 系   ：覆盖 77 token，核心内容不被截断
  · FLUX-schnell ：在最优注意力区间（60-80 词），主体聚焦
  · 结构优先级   ：质量锚点 → 主体细节 → 光影 → 镜头 → 氛围
                  （最重要的词放最前，即使截断也保留核心）

【写实人像专项优化】
  · 前 5-8 词固定包含写实质量锚点（photorealistic/RAW photo）
  · 每个维度严格提炼为 1-3 个最具表现力的短语
  · 避免重复/冗余/纯装饰性词语
  · temperature 降至 0.60，减少"创意漂移"

模型优先级（v3 已设置，v4 继承）：
  ─ 第一梯队：DeepSeek V3-0324 / DeepSeek V3
  ─ 第二梯队：Qwen2.5-72B / Qwen2.5-32B
  ─ 第三梯队：GLM-4-9B（兜底）
"""
import re
import requests

# ══════════════════════════════════════════════════════════════
#   Token 预算常量
# ══════════════════════════════════════════════════════════════
# 目标：58-72 词，硬上限 80 词（超出时后处理截断）
_WORD_TARGET_MIN = 58
_WORD_TARGET_MAX = 72
_WORD_HARD_CAP   = 80     # 后处理截断阈值

# ══════════════════════════════════════════════════════════════
#   系统提示词 v4：严格词数控制 + 写实优先结构
# ══════════════════════════════════════════════════════════════
_SYSTEM = """\
You are a professional Stable Diffusion / FLUX prompt engineer specialized in photorealistic results.

Convert the user's parameters into ONE English image generation prompt.

━━━ HARD RULES (non-negotiable) ━━━
1. OUTPUT: Only the final prompt text. No labels, no markdown, no quotes, no explanation.
2. LANGUAGE: English only (translate all Chinese inputs).
3. WORD COUNT: EXACTLY 58–72 words. Count every word. Do NOT exceed 72 words.
4. FORMAT: Comma-separated short phrases. No full sentences. No conjunctions.

━━━ STRUCTURE (strict order, frontload the important items) ━━━
Slot 1 [words 1-6]   QUALITY ANCHORS — Must open with: photorealistic, RAW photo
                     Then add 1-2 of: sharp focus / masterpiece / best quality
Slot 2 [words 7-22]  SUBJECT — age, ethnicity, gender, expression, clothing, pose
                     + key physical detail (skin texture OR hair OR eyes, pick ONE)
Slot 3 [words 23-38] SCENE & LIGHTING — location/background + ONE specific light source
                     (e.g. soft natural window light / golden hour backlight)
Slot 4 [words 39-54] CAMERA — lens mm + aperture (e.g. 85mm f/1.4, shallow depth of field)
                     + one composition note (e.g. medium close-up, rule of thirds)
Slot 5 [words 55-72] STYLE & MOOD — one style label + one mood/color tone phrase
                     + optional: 8K UHD / cinematic color grade

━━━ PHOTOREALISM RULES ━━━
• Lead with "photorealistic, RAW photo" — these tokens must NOT be displaced
• Choose ONE dominant style — mixing "photorealistic" with "oil painting" kills realism
• For portraits: always include a specific lens (85mm/50mm) and skin texture descriptor
• Avoid vague filler words: "beautiful", "stunning", "amazing", "wonderful", "incredible"
• Prefer precise technical terms: "porcelain skin" > "beautiful skin"

━━━ WORD COUNT CHECK ━━━
Before outputting: count your words. If >72, cut the lowest-priority words from Slot 5.
"""

# ══════════════════════════════════════════════════════════════
#   硅基流动模型候选列表（按优先级从高到低）
#   ① DeepSeek V3 系列（最优先，写作指令遵循最强）
#   ② Qwen2.5 系列（第二梯队）
#   ③ GLM-4（兜底）
# ══════════════════════════════════════════════════════════════
_SF_MODELS = [
    # ─── 第一梯队：DeepSeek V3 系列 ──────────────────────────
    "deepseek-ai/DeepSeek-V3-0324",   # 首选：最新版 V3，指令遵循最强
    "deepseek-ai/DeepSeek-V3",        # 备用：原版 V3，稳定
    # ─── 第二梯队：Qwen2.5 系列 ──────────────────────────────
    "Qwen/Qwen2.5-72B-Instruct",      # 千问旗舰 72B，英文创作强
    "Qwen/Qwen2.5-32B-Instruct",      # 千问 32B，速度均衡
    # ─── 第三梯队：其他开源兜底 ──────────────────────────────
    "THUDM/glm-4-9b-chat",            # GLM-4 轻量兜底
]

# ── HuggingFace 备用通道（硅基流动完全不可用时）──────────────
_HF_MODELS = [
    "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "HuggingFaceH4/zephyr-7b-beta",
]

# ── 模型展示名（用于日志和 UI 提示，更易读）────────────────────
_SF_MODEL_LABELS = {
    "deepseek-ai/DeepSeek-V3-0324":  "DeepSeek V3-0324 🥇",
    "deepseek-ai/DeepSeek-V3":       "DeepSeek V3",
    "Qwen/Qwen2.5-72B-Instruct":     "Qwen2.5-72B",
    "Qwen/Qwen2.5-32B-Instruct":     "Qwen2.5-32B",
    "THUDM/glm-4-9b-chat":           "GLM-4-9B",
}

# ══════════════════════════════════════════════════════════════
#   负面提示词词库（分类，供 UI 选取）
# ══════════════════════════════════════════════════════════════
NEGATIVE_LIBRARY = {
    "通用质量": (
        "lowres, bad anatomy, bad hands, text, error, missing fingers, "
        "extra digit, fewer digits, cropped, worst quality, low quality, "
        "normal quality, jpeg artifacts, signature, watermark, username, blurry"
    ),
    "人物专用": (
        "deformed, mutated, ugly, disfigured, bad proportions, "
        "extra limbs, cloned face, gross proportions, malformed limbs, "
        "missing arms, missing legs, extra arms, extra legs, fused fingers, "
        "too many fingers, long neck"
    ),
    "写实/摄影": (
        "painting, illustration, 3d render, cartoon, anime, sketch, "
        "drawing, art, unrealistic, fake, cgi, digital art"
    ),
    "动漫/插画": (
        "photo, realistic, photograph, 3d, cgi, render, "
        "bad drawn face, bad drawn hands, poorly drawn, "
        "out of frame, extra fingers, mutated hands"
    ),
    "商业/封面": (
        "amateur, unprofessional, cluttered, messy background, "
        "overexposed, underexposed, motion blur, out of focus, "
        "low resolution, pixelated, grainy, noise"
    ),
    "无负面词": "",
}

# ══════════════════════════════════════════════════════════════
#   自媒体平台专用模板库
# ══════════════════════════════════════════════════════════════
TEMPLATES = {
    # ══════════════════════════════════════════════════════════
    # ── 小红书系列 ─────────────────────────────────────────
    # ══════════════════════════════════════════════════════════
    "xhs_hot": {
        "name": "🌸 小红书爆款封面",
        "category": "小红书",
        "desc": "高饱和度甜美风，强烈视觉冲击，适合美食/美妆/生活方式",
        "keywords_hint": "人物主题（如：咖啡女孩、护肤品、甜品）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, young East Asian woman, bright smile, trendy outfit, "
            "holding {prop_hint}, "
            "soft pink and white pastel background, "
            "warm golden sunlight, bokeh, "
            "85mm portrait lens f/1.8, shallow depth of field, "
            "vivid saturated colors, clean minimal composition, "
            "Instagram lifestyle photography, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "3:4 (小红书竖版封面)",
        "tips": "建议尺寸 768×1024 或 1024×1365",
    },
    "xhs_travel": {
        "name": "✈️ 小红书旅行打卡",
        "category": "小红书",
        "desc": "旅行目的地风光，适合探店/旅游攻略封面",
        "keywords_hint": "目的地/景点（如：京都街道、海边日落、云南古镇）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, picturesque travel destination, "
            "dramatic natural landscape, golden hour lighting, warm amber tones, "
            "wide angle shot, vast panoramic view, vivid colors, crystal sky, "
            "travel lifestyle photography, National Geographic style, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "3:4 或 1:1",
        "tips": "建议尺寸 1024×1024 方形或 768×1024 竖版",
    },
    "xhs_food": {
        "name": "🍜 小红书美食探店",
        "category": "小红书",
        "desc": "精致食物特写，食欲感强，适合美食博主",
        "keywords_hint": "食物名称（如：抹茶千层蛋糕、炙烤和牛、草莓塔）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, gourmet food photography, "
            "elegant plating on fine ceramic dish, steam rising, fresh ingredients, "
            "warm soft window light, shallow depth of field, "
            "85mm lens f/2.0, bokeh background, appetizing texture, "
            "professional food editorial, Michelin quality, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "1:1 或 4:3",
        "tips": "建议尺寸 1024×1024 方形效果最佳",
    },
    "xhs_beauty": {
        "name": "💄 小红书美妆种草",
        "category": "小红书",
        "desc": "美妆产品平铺或上妆效果，适合护肤/彩妆种草笔记",
        "keywords_hint": "产品/妆容（如：口红唇妆、精华瓶平铺、晨间护肤routine）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, beauty product flat lay, "
            "luxurious cosmetics arranged on white marble surface, "
            "soft diffused natural light, clean pastel background, "
            "overhead top-down view, flawless skin texture close-up, "
            "60mm macro lens, crisp details, "
            "beauty editorial magazine style, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "1:1 或 3:4",
        "tips": "建议尺寸 1024×1024，留白多=高级感",
    },
    "xhs_outfit": {
        "name": "👗 小红书穿搭分享",
        "category": "小红书",
        "desc": "全身穿搭展示，街拍感，适合时尚/穿搭博主",
        "keywords_hint": "穿搭风格（如：法式复古、简约通勤、Y2K风格）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, full body outfit photo, "
            "young East Asian woman, stylish fashion look, "
            "natural outdoor urban setting, dappled sunlight, "
            "candid street style photography, soft bokeh background, "
            "35mm lens, relaxed natural pose, "
            "fashion editorial vibe, VSCO film aesthetic, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "3:4 竖版",
        "tips": "建议尺寸 768×1024，全身竖构图最适合穿搭展示",
    },

    # ══════════════════════════════════════════════════════════
    # ── 情绪爆款系列 ──────────────────────────────────────
    # ══════════════════════════════════════════════════════════
    "emotion_dramatic": {
        "name": "🔥 高点击率情绪大片",
        "category": "情绪爆款",
        "desc": "强烈戏剧性情绪，高对比度，极具冲击力的封面",
        "keywords_hint": "情绪主题（如：破釜沉舟、逆风前行、孤注一掷）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, intense emotional portrait, "
            "dramatic cinematic lighting, deep shadows, bright highlights, "
            "stormy sky background, ultra close-up, raw authentic expression, "
            "35mm cinematic lens, shallow depth of field, "
            "teal and orange color grade, epic cinematic style, 8K hyper realistic"
        ),
        "negative": NEGATIVE_LIBRARY["通用质量"],
        "size_hint": "16:9 横版或 9:16 竖版",
        "tips": "建议尺寸 1280×720 横版 或 720×1280 竖版",
    },
    "emotion_healing": {
        "name": "💛 温暖治愈系封面",
        "category": "情绪爆款",
        "desc": "温柔治愈氛围，适合情感/心理/生活感悟类内容",
        "keywords_hint": "情感场景（如：午后独处、窗边阅读、雨天咖啡）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, soft warm healing atmosphere, "
            "gentle afternoon sunlight filtering through curtains, golden hour glow, "
            "peaceful expression, cozy interior, pastel warm tones, cream palette, "
            "50mm lens f/2.8, medium portrait, film aesthetic, "
            "tender nostalgic mood, natural authentic"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "9:16 竖版",
        "tips": "建议尺寸 720×1280，温暖色调更容易引发共鸣",
    },
    "emotion_aesthetic": {
        "name": "🌙 高级感氛围大图",
        "category": "情绪爆款",
        "desc": "暗调高级质感，适合时尚/艺术/品味类账号",
        "keywords_hint": "氛围主题（如：深夜独处、城市孤独、极简主义）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, dark moody editorial photography, "
            "dramatic chiaroscuro lighting, deep blacks, luxury fashion aesthetic, "
            "85mm f/1.4 lens, ultra sharp focus, soft background blur, "
            "desaturated elegant tones, strong negative space, "
            "Vogue editorial style, ultra high resolution"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "4:5 或 1:1",
        "tips": "建议尺寸 1024×1280，暗调可让主题更突出",
    },
    "emotion_motivation": {
        "name": "⚡ 励志奋斗封面",
        "category": "情绪爆款",
        "desc": "冲劲感强，适合职场成长/考研/副业变现类内容",
        "keywords_hint": "奋斗场景（如：深夜自习室、黎明跑步、成功登顶）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, determined ambitious person, "
            "first-person perspective mountain summit or city skyline, "
            "early morning sunrise golden rays, dramatic lens flare, "
            "wide angle 24mm, dynamic low angle shot, "
            "warm orange red cinematic color grade, "
            "powerful motivational energy, epic dawn atmosphere, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["通用质量"],
        "size_hint": "16:9 横版或 9:16 竖版",
        "tips": "建议尺寸 1280×720，日出构图感染力最强",
    },

    # ══════════════════════════════════════════════════════════
    # ── 知识干货系列 ──────────────────────────────────────
    # ══════════════════════════════════════════════════════════
    "knowledge_clean": {
        "name": "📚 知识干货封面",
        "category": "知识干货",
        "desc": "清晰简洁，专业可信，适合教育/职场/知识分享",
        "keywords_hint": "知识主题（如：时间管理、学习方法、职场沟通）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, professional knowledge concept, "
            "clean minimal flat lay, notebook pen charts arranged neatly, "
            "soft natural window light, white background, "
            "overhead bird eye view, corporate aesthetic, "
            "high key lighting, crisp clear, business editorial, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "1:1 或 16:9",
        "tips": "建议尺寸 1024×1024，留出文字区域",
    },
    "knowledge_tech": {
        "name": "💻 科技感知识封面",
        "category": "知识干货",
        "desc": "科技未来感，适合AI/科技/数据/程序类内容",
        "keywords_hint": "技术主题（如：人工智能、大数据、量子计算、编程）",
        "positive_template": (
            "{subject}, futuristic technology visualization, "
            "glowing neon blue cyan digital interface, "
            "holographic data streams circuit patterns, dark background, "
            "luminous tech elements, ultra wide cinematic shot, "
            "dramatic blue purple neon lighting, cyberpunk digital art, "
            "sharp geometric composition, 8K ultra detailed CGI render"
        ),
        "negative": NEGATIVE_LIBRARY["写实/摄影"],
        "size_hint": "16:9 横版",
        "tips": "建议尺寸 1280×720，横版更适合科技感构图",
    },
    "knowledge_finance": {
        "name": "💰 财经理财封面",
        "category": "知识干货",
        "desc": "专业稳重，适合财经/投资/职场成长类内容",
        "keywords_hint": "财经主题（如：基金定投、副业收入、职场晋升）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, professional business portrait, "
            "confident expression, premium office interior, city skyline, "
            "natural window lighting, warm professional tones, navy gold palette, "
            "35mm lens slight low angle, Forbes magazine quality, "
            "corporate editorial photography, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "1:1 或 16:9",
        "tips": "建议尺寸 1024×1024，专业感强",
    },
    "knowledge_health": {
        "name": "🏃 健康运动封面",
        "category": "知识干货",
        "desc": "活力健康感，适合健身/养生/减脂/运动类内容",
        "keywords_hint": "健康主题（如：早起锻炼、健康饮食、瑜伽冥想、减脂餐）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, healthy active lifestyle, "
            "athletic person in natural outdoor setting, "
            "fresh morning light, lush green background, "
            "dynamic movement frozen, 50mm f/2.0 lens, "
            "vibrant energetic colors, clean healthy aesthetic, "
            "sports lifestyle photography, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "1:1 或 4:3",
        "tips": "建议尺寸 1024×1024，方形构图兼容多平台",
    },

    # ══════════════════════════════════════════════════════════
    # ── 微信公众号系列（新增）───────────────────────────
    # ══════════════════════════════════════════════════════════
    "wechat_header": {
        "name": "📰 公众号头图（横版）",
        "category": "微信公众号",
        "desc": "文章头图，横版宽幅，专业感强，适合各类公众号推文",
        "keywords_hint": "文章主题（如：职场干货、行业洞察、产品发布、节日祝福）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, professional magazine cover style, "
            "wide panoramic composition, clean minimal background, "
            "dramatic cinematic side lighting, rich deep colors, "
            "16:9 aspect ratio, ample negative space on right for text, "
            "24mm wide lens, high dynamic range, "
            "editorial publication quality, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "16:9 横版（公众号标准头图）",
        "tips": "建议尺寸 1440×810 或 900×500，右侧留空放文字",
    },
    "wechat_square": {
        "name": "🟦 公众号封面方图",
        "category": "微信公众号",
        "desc": "朋友圈分享封面，方形构图，抢眼吸睛",
        "keywords_hint": "内容主题（如：新品上市、活动预告、知识干货、人生感悟）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, premium brand visual, "
            "bold centered composition, symmetrical layout, "
            "clean gradient or solid color background, "
            "dramatic studio lighting, crisp sharp details, "
            "commercial photography, square 1:1 format, "
            "high saturation brand colors, advertising quality, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "1:1 方形",
        "tips": "建议尺寸 900×900，居中构图在朋友圈缩略图中最显眼",
    },
    "wechat_narrative": {
        "name": "✍️ 公众号故事叙事图",
        "category": "微信公众号",
        "desc": "情感共鸣型配图，适合深度文章、故事叙述类公众号",
        "keywords_hint": "故事情感（如：创业故事、人生转折、城市孤独、时光流逝）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, documentary storytelling photography, "
            "candid intimate moment, natural available light, "
            "slightly desaturated warm film tones, grain texture, "
            "35mm f/2.0 lens, medium shot, environmental portrait, "
            "emotional authentic atmosphere, "
            "editorial narrative photography, timeless quality"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "16:9 横版或 3:2",
        "tips": "建议尺寸 1440×960，胶片感色调增加阅读代入感",
    },
    "wechat_festive": {
        "name": "🎉 公众号节日运营图",
        "category": "微信公众号",
        "desc": "节假日推文配图，喜庆氛围，适合各类节日营销内容",
        "keywords_hint": "节日名称（如：春节、中秋、元旦、情人节、618）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, festive holiday celebration atmosphere, "
            "vibrant warm celebratory colors, bokeh light effects, "
            "joyful golden red palette, festive decorations, "
            "wide shot, dynamic composition, "
            "advertising commercial photography, "
            "festive mood, professional brand editorial, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "16:9 横版或 1:1",
        "tips": "建议尺寸 900×500 或 900×900，预留文字区域在图片下方",
    },
    "wechat_brand": {
        "name": "🏢 公众号品牌宣传图",
        "category": "微信公众号",
        "desc": "企业/品牌形象展示，高端大气，适合品宣/企业号",
        "keywords_hint": "品牌主题（如：科技公司、餐饮品牌、教育机构、零售门店）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, premium corporate brand photography, "
            "sleek modern office or flagship store environment, "
            "confident professional team or signature product, "
            "natural window light with dramatic shadows, "
            "24-70mm zoom lens, architectural composition, "
            "corporate identity colors, Forbes 500 quality, "
            "brand storytelling editorial, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "16:9 横版",
        "tips": "建议尺寸 1440×810，横版最适合展示品牌气质",
    },

    # ══════════════════════════════════════════════════════════
    # ── 电商产品系列 ──────────────────────────────────────
    # ══════════════════════════════════════════════════════════
    "ecom_product": {
        "name": "🛍️ 电商产品主图",
        "category": "电商产品",
        "desc": "产品展示主图，干净背景，突出产品细节",
        "keywords_hint": "产品名称（如：护肤精华瓶、运动鞋、无线耳机、手机壳）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, professional product photography, "
            "clean white background, studio lighting, three-point light setup, "
            "soft shadows, crisp product details, "
            "50mm macro lens, perfect exposure, "
            "e-commerce style, commercial product shoot, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "1:1 (电商标准方图)",
        "tips": "建议尺寸 1024×1024，白底产品图标准格式",
    },
    "ecom_lifestyle": {
        "name": "✨ 电商场景生活图",
        "category": "电商产品",
        "desc": "产品融入生活场景，增加代入感和购买欲",
        "keywords_hint": "产品+场景（如：咖啡机+厨房晨光、运动装备+户外、书桌+学习氛围）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, lifestyle product photography in context, "
            "natural home interior setting, soft window light, "
            "warm cozy atmosphere, product prominently featured, "
            "35mm lens f/2.8, slight bokeh background, "
            "editorial lifestyle shot, authentic natural feel, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "4:3 或 16:9",
        "tips": "建议尺寸 1024×768，横版场景感更强",
    },
    "ecom_detail": {
        "name": "🔍 电商产品细节图",
        "category": "电商产品",
        "desc": "极致细节特写，展示材质/纹理/工艺，增强信任感",
        "keywords_hint": "产品材质/细节（如：皮革纹理、金属拉丝、刺绣工艺、液体流动）",
        "positive_template": (
            "photorealistic, RAW photo, macro sharp focus, "
            "{subject}, extreme close-up product detail, "
            "ultra fine texture revealed, material quality emphasized, "
            "controlled studio macro lighting, soft box fill light, "
            "100mm macro lens f/4.0, crisp texture, "
            "premium material showcase, advertising quality, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "1:1 或 4:3",
        "tips": "建议尺寸 1024×1024，细节图展示品质感",
    },
    "ecom_livestream": {
        "name": "📺 直播间背景图",
        "category": "电商产品",
        "desc": "直播间背景/封面，吸引点击，适合各类直播带货",
        "keywords_hint": "直播主题（如：美妆专场、服装秋冬、食品零食、家居好物）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, professional live streaming background, "
            "colorful vibrant product display, "
            "well-lit studio environment, promotional atmosphere, "
            "wide angle 24mm, clean organized layout, "
            "bold eye-catching colors, retail commercial style, "
            "high energy sales vibe, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "16:9 横版",
        "tips": "建议尺寸 1280×720，横版直播间背景标准格式",
    },

    # ══════════════════════════════════════════════════════════
    # ── 视频封面系列 ──────────────────────────────────────
    # ══════════════════════════════════════════════════════════
    "video_youtube": {
        "name": "▶️ YouTube/B站视频封面",
        "category": "视频封面",
        "desc": "高对比度缩略图，远看也能识别，适合 YouTube/B站",
        "keywords_hint": "视频主题（如：开箱测评、旅行vlog、美食探店、科技评测）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, YouTube thumbnail style, "
            "bold dramatic lighting, high contrast, vivid colors, "
            "medium close-up shot, engaging expressive face, "
            "clean bold background, strong visual hierarchy, "
            "35mm lens, professional studio look, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["通用质量"],
        "size_hint": "16:9 横版",
        "tips": "建议尺寸 1280×720，确保人脸在右侧留出文字空间",
    },
    "video_short": {
        "name": "📱 短视频竖版封面",
        "category": "视频封面",
        "desc": "竖版构图，手机优先，适合抖音/快手/Reels",
        "keywords_hint": "视频亮点（如：街头舞蹈、Vlog日常、搞笑挑战、才艺展示）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, vertical short video thumbnail, "
            "dynamic energetic composition, bold colors, "
            "dramatic lighting, expressive gesture, "
            "50mm lens f/1.8, slight bokeh, "
            "mobile-first framing, eye-catching composition, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["通用质量"],
        "size_hint": "9:16 竖版",
        "tips": "建议尺寸 720×1280，竖版最适合移动端观看",
    },
    "video_podcast": {
        "name": "🎙️ 播客/访谈封面",
        "category": "视频封面",
        "desc": "专业访谈氛围，适合播客/对话/访谈类视频节目",
        "keywords_hint": "节目主题（如：创业对话、职场故事、投资观点、读书分享）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, professional podcast interview setup, "
            "warm intimate studio environment, microphone visible, "
            "soft key light with warm fill, subtle bokeh background, "
            "50mm f/1.8 lens, medium shot, "
            "intellectual conversational atmosphere, "
            "NPR documentary style, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "16:9 横版或 1:1",
        "tips": "建议尺寸 1280×720，人物居中或双人对话构图",
    },

    # ══════════════════════════════════════════════════════════
    # ── AI 与数字艺术系列（新增）────────────────────────
    # ══════════════════════════════════════════════════════════
    "art_concept": {
        "name": "🎨 概念艺术插画",
        "category": "AI数字艺术",
        "desc": "高品质概念艺术，适合壁纸/插画/创意展示",
        "keywords_hint": "艺术主题（如：赛博城市夜景、奇幻森林精灵、宇宙星云、水墨山水）",
        "positive_template": (
            "{subject}, stunning concept art, "
            "hyperdetailed digital painting, artstation quality, "
            "epic cinematic composition, dramatic atmospheric lighting, "
            "rich saturated colors, intricate fine details, "
            "award-winning illustration, 8K UHD resolution, "
            "trending on ArtStation, Greg Rutkowski style"
        ),
        "negative": NEGATIVE_LIBRARY["写实/摄影"],
        "size_hint": "16:9 横版或 4:3",
        "tips": "建议尺寸 1280×720，横版展示全景艺术效果最佳",
    },
    "art_portrait": {
        "name": "🖼️ 艺术风人像",
        "category": "AI数字艺术",
        "desc": "带有艺术风格的人像，适合头像/社交媒体/NFT",
        "keywords_hint": "风格+人物（如：水彩女孩、赛博朋克少年、油画古典美人）",
        "positive_template": (
            "{subject}, artistic portrait, "
            "detailed face, expressive eyes, "
            "masterpiece quality illustration, "
            "perfect lighting, vibrant colors, "
            "intricate background details, "
            "professional digital art, trending on ArtStation, "
            "4K ultra detailed, cinematic composition"
        ),
        "negative": NEGATIVE_LIBRARY["动漫/插画"],
        "size_hint": "1:1 或 3:4",
        "tips": "建议尺寸 1024×1024，方形最适合头像用途",
    },
    "art_wallpaper": {
        "name": "🌌 桌面壁纸",
        "category": "AI数字艺术",
        "desc": "震撼视觉的宽幅壁纸，适合桌面/手机壁纸",
        "keywords_hint": "壁纸主题（如：星空银河、深海蓝鲸、赛博都市、极简几何）",
        "positive_template": (
            "{subject}, epic wallpaper artwork, "
            "ultra wide panoramic view, "
            "breathtaking scenery, stunning visual spectacle, "
            "volumetric atmospheric lighting, god rays, "
            "deep rich colors, majestic scale, "
            "hyperdetailed 8K wallpaper, "
            "cinematic widescreen composition, award-winning photography"
        ),
        "negative": NEGATIVE_LIBRARY["通用质量"],
        "size_hint": "16:9 或 21:9 超宽",
        "tips": "建议尺寸 1920×1080，超宽屏可用 2560×1080",
    },

    # ══════════════════════════════════════════════════════════
    # ── 品牌与营销系列（新增）───────────────────────────
    # ══════════════════════════════════════════════════════════
    "brand_product_launch": {
        "name": "🚀 产品发布图",
        "category": "品牌营销",
        "desc": "科技感产品发布宣传图，适合新品上市/发布会海报",
        "keywords_hint": "产品名+品类（如：旗舰手机、智能手表、蓝牙耳机、电动汽车）",
        "positive_template": (
            "photorealistic, sharp focus, "
            "{subject}, premium product launch photography, "
            "floating isolated on dark background, "
            "dramatic rim lighting, neon accent glow, "
            "reflective surface, sleek tech aesthetic, "
            "Apple-style product photography, "
            "minimalist dark background, 8K studio render"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "16:9 或 1:1",
        "tips": "建议尺寸 1280×720，深色背景更突出产品质感",
    },
    "brand_social_ad": {
        "name": "📣 社交媒体广告图",
        "category": "品牌营销",
        "desc": "信息流广告图，吸引点击，适合各平台投放",
        "keywords_hint": "广告内容（如：限时优惠、会员招募、活动报名、课程推广）",
        "positive_template": (
            "photorealistic, RAW photo, sharp focus, "
            "{subject}, social media advertisement, "
            "attention-grabbing bold composition, "
            "happy satisfied customer or aspirational lifestyle, "
            "vibrant brand colors, clean minimal layout, "
            "35mm lens, professional advertising photography, "
            "conversion-optimized visual hierarchy, 8K"
        ),
        "negative": NEGATIVE_LIBRARY["商业/封面"],
        "size_hint": "1:1 或 4:5",
        "tips": "建议尺寸 1080×1080，方形在 Instagram/微博 中表现最佳",
    },
    "brand_infographic": {
        "name": "📊 数据可视化配图",
        "category": "品牌营销",
        "desc": "清晰的数据/概念可视化图，适合报告/文章/演示",
        "keywords_hint": "数据主题（如：增长趋势、市场份额、用户画像、行业对比）",
        "positive_template": (
            "{subject}, modern data visualization concept, "
            "clean professional infographic style, "
            "glowing geometric charts graphs, "
            "dark navy blue background, cyan accent colors, "
            "precise grid layout, tech corporate aesthetic, "
            "Bloomberg style financial data visual, "
            "sharp clean lines, 8K CGI render"
        ),
        "negative": NEGATIVE_LIBRARY["写实/摄影"],
        "size_hint": "16:9 横版",
        "tips": "建议尺寸 1280×720，横版更适合展示数据图表",
    },
}


# 按 category 分组（供 UI 渲染）
def get_templates_by_category() -> dict:
    cats = {}
    for tid, t in TEMPLATES.items():
        cat = t["category"]
        cats.setdefault(cat, [])
        cats[cat].append((tid, t))
    return cats


# ══════════════════════════════════════════════════════════════
#   Token 预算后处理器
# ══════════════════════════════════════════════════════════════
def _trim_to_budget(text: str, max_words: int = _WORD_HARD_CAP) -> str:
    """
    智能截断提示词到 max_words 词以内。

    策略（按优先级）：
    1. 如果词数 ≤ max_words，直接返回
    2. 按逗号短语分割，从末尾逐一删除短语，直到符合预算
    3. 保证至少保留前 4 个短语（质量锚点 + 主体核心）

    同时做文本清理：去除重复短语、多余空格。
    """
    # 先做基础清理
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(".,; ")

    words = text.split()
    if len(words) <= max_words:
        return text

    # 按逗号分割短语
    phrases = [p.strip() for p in text.split(",") if p.strip()]

    # 去重（保持顺序）
    seen = set()
    deduped = []
    for p in phrases:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    phrases = deduped

    # 从末尾逐一删除短语直到词数 ≤ max_words
    while len(phrases) > 4:
        candidate = ", ".join(phrases)
        if len(candidate.split()) <= max_words:
            break
        phrases.pop()   # 删除最后一个短语

    result = ", ".join(phrases)
    return result.strip("., ")


def _count_words(text: str) -> int:
    """统计英文单词数（简单空格分割）。"""
    return len(text.split())


def prompt_budget_info(text: str) -> dict:
    """
    返回提示词的预算信息，供 UI 展示。

    Returns
    -------
    {
        "words":    int,      词数
        "chars":    int,      字符数
        "status":   str,      "optimal" | "acceptable" | "too_long"
        "label":    str,      UI 展示标签
        "color":    str,      状态颜色（十六进制）
        "models_ok": list,    当前长度下兼容的模型列表
        "trimmed":  str,      如需压缩，给出压缩后的版本；否则同原文
    }
    """
    w = _count_words(text)
    c = len(text)

    if w <= _WORD_TARGET_MAX:           # ≤ 72 词：最优
        status = "optimal"
        label  = f"✅ 最优  {w} 词 / {c} 字符"
        color  = "#4ecca3"
        models_ok = ["FLUX.1-schnell", "SDXL", "SD 2.1", "SD 1.5"]
    elif w <= _WORD_HARD_CAP:           # 73-80 词：可接受
        status = "acceptable"
        label  = f"⚠️ 偏长  {w} 词 / {c} 字符"
        color  = "#f0a500"
        models_ok = ["FLUX.1-schnell（部分细节略弱）"]
    else:                               # > 80 词：过长
        status = "too_long"
        label  = f"❌ 过长  {w} 词 / {c} 字符（SDXL/SD 将被截断）"
        color  = "#e94560"
        models_ok = []

    trimmed = _trim_to_budget(text, _WORD_HARD_CAP) if w > _WORD_HARD_CAP else text

    return {
        "words":     w,
        "chars":     c,
        "status":    status,
        "label":     label,
        "color":     color,
        "models_ok": models_ok,
        "trimmed":   trimmed,
    }


# ══════════════════════════════════════════════════════════════
#   主函数：全维度参数生成
# ══════════════════════════════════════════════════════════════
def generate_prompt(
    keywords:    str,
    cfg:         dict,
    style:       str = "",
    mood:        str = "",
    detail:      str = "",
    composition: str = "",
    lighting:    str = "",
    camera:      str = "",
    quality:     str = "",
    negative:    str = "",
    extra:       str = "",
    log_cb=None,
) -> tuple:
    """
    Returns
    -------
    (positive_prompt: str, negative_prompt: str)
    """
    def log(msg):
        if log_cb: log_cb(msg)

    # ── 组装结构化用户消息 ─────────────────────────────────────
    parts = [f"主题关键词: {keywords}"]
    if style:       parts.append(f"风格 (Style): {style}")
    if mood:        parts.append(f"氛围/情绪 (Mood): {mood}")
    if detail:      parts.append(f"细节要求 (Detail): {detail}")
    if composition: parts.append(f"构图方式 (Composition): {composition}")
    if lighting:    parts.append(f"光影类型 (Lighting): {lighting}")
    if camera:      parts.append(f"镜头参数 (Camera): {camera}")
    if quality:     parts.append(f"画质增强 (Quality): {quality}")
    if extra:       parts.append(f"额外说明: {extra}")
    user_msg = "\n".join(parts)

    sf_key = cfg.get("sf_key", "").strip()
    hf_tok = cfg.get("hf_token", "").strip()

    if sf_key:
        positive = _call_siliconflow(sf_key, user_msg, log)
    elif hf_tok:
        positive = _call_huggingface(hf_tok, user_msg, log)
    else:
        raise ValueError(
            "提示词助手需要配置 API Key。\n\n"
            "推荐：在「🆓 免费配置」中填写「硅基流动」API Key。\n"
            "注册地址：https://cloud.siliconflow.cn"
        )

    # ── 后处理：超预算时智能截断 ───────────────────────────────
    w_before = _count_words(positive)
    if w_before > _WORD_HARD_CAP:
        positive = _trim_to_budget(positive, _WORD_HARD_CAP)
        w_after = _count_words(positive)
        log(f"✂️ 提示词超出预算（{w_before} 词 → {w_after} 词），已自动压缩")
    else:
        log(f"📊 提示词: {w_before} 词 / {len(positive)} 字符")

    return positive, negative


# ══════════════════════════════════════════════════════════════
#   模板模式：直接填充，无需调用 LLM
# ══════════════════════════════════════════════════════════════
def apply_template(
    template_id: str,
    keywords:    str,
    cfg:         dict = None,
    log_cb=None,
) -> tuple:
    """用关键词填充模板，立即返回 (positive, negative)，无网络请求。"""
    def log(msg):
        if log_cb: log_cb(msg)

    if template_id not in TEMPLATES:
        raise ValueError(f"未知模板 ID: {template_id}")

    t = TEMPLATES[template_id]
    pos = t["positive_template"]

    subject = keywords.strip() if keywords.strip() else "a person"
    pos = pos.replace("{subject}", subject)

    prop_hints = {
        "美食": "a beautifully plated dish",
        "咖啡": "a latte art coffee cup",
        "花":   "a bouquet of fresh flowers",
        "书":   "an open book",
    }
    prop = "a lifestyle product"
    for kw, hint in prop_hints.items():
        if kw in keywords:
            prop = hint; break
    pos = pos.replace("{prop_hint}", prop)

    neg = t.get("negative", NEGATIVE_LIBRARY["通用质量"])
    log(f"📋 模板「{t['name']}」已应用: {pos[:60]}…")
    return pos, neg


# ══════════════════════════════════════════════════════════════
#   API 调用实现
# ══════════════════════════════════════════════════════════════
def _call_siliconflow(api_key: str, user_msg: str, log) -> str:
    """
    按 _SF_MODELS 顺序逐一尝试，首个成功即返回。
    优先级：DeepSeek V3-0324 → DeepSeek V3 → Qwen2.5-72B → Qwen2.5-32B → GLM-4
    """
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    for model in _SF_MODELS:
        label = _SF_MODEL_LABELS.get(model, model)
        log(f"🤖 提示词助手 › {label}…")
        try:
            resp = requests.post(url, headers=headers, json={
                "model":    model,
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user",   "content": user_msg},
                ],
                # v4 关键参数调整：
                # · temperature 0.60（↓ 0.72）— 减少发散，提高指令遵循精准度
                # · max_tokens  160 — 72词×平均2.1 token/词≈151，留10 buffer
                #   严格控制输出长度，防止 DeepSeek 过度生成
                "temperature": 0.60,
                "max_tokens":  160,
                "stream":      False,
            }, timeout=40)

            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()
                text = _clean(text)
                if len(text) < 20:
                    log(f"  {label}: 返回内容过短，尝试下一个模型")
                    continue
                log(f"✅ {label} 成功（{_count_words(text)} 词 / {len(text)} 字符）")
                return text

            elif resp.status_code in (404, 422):
                log(f"  {label}: 模型不可用 (HTTP {resp.status_code})，跳过")
                continue
            elif resp.status_code == 429:
                log(f"  {label}: 请求频率超限 (429)，跳过")
                continue
            elif resp.status_code in (401, 403):
                raise ValueError(
                    f"API Key 无效或权限不足 (HTTP {resp.status_code})，"
                    "请在「免费配置」中重新填写硅基流动 Key。"
                )
            else:
                log(f"  {label}: HTTP {resp.status_code}，跳过")
                continue

        except requests.Timeout:
            log(f"  {label}: 请求超时，跳过")
            continue
        except ValueError:
            raise
        except Exception as ex:
            log(f"  {label}: {ex}，跳过")
            continue

    raise ValueError(
        "提示词助手：硅基流动所有候选模型均不可用。\n\n"
        "可能原因：\n"
        "  · 网络问题（请检查代理/防火墙）\n"
        "  · 账号余额不足（请登录 siliconflow.cn 充值）\n"
        "  · 当前套餐不包含所选模型\n\n"
        "候选模型列表：\n"
        + "\n".join(f"  {i+1}. {_SF_MODEL_LABELS.get(m, m)}"
                    for i, m in enumerate(_SF_MODELS))
    )


def _call_huggingface(token: str, user_msg: str, log) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    for model in _HF_MODELS:
        log(f"🤖 提示词助手 › HF {model}…")
        url    = f"https://api-inference.huggingface.co/models/{model}"
        prompt = f"<s>[INST] {_SYSTEM}\n\nUser request:\n{user_msg} [/INST]"
        try:
            resp = requests.post(url, headers=headers, json={
                "inputs":     prompt,
                "parameters": {
                    "max_new_tokens":   160,   # 同步限制
                    "temperature":      0.60,
                    "return_full_text": False,
                },
            }, timeout=45)
            if resp.status_code == 200:
                result = resp.json()
                if isinstance(result, list) and result:
                    text = result[0].get("generated_text", "").strip()
                    text = _clean(text)
                    if len(text) > 20:
                        log(f"✓ HF {model} 成功（{_count_words(text)} 词）")
                        return text
            log(f"  HF {model}: HTTP {resp.status_code}")
        except Exception as ex:
            log(f"  HF {model}: {ex}")
    raise ValueError("HuggingFace 模型均不可用，请改用硅基流动")


def _clean(text: str) -> str:
    """清理 LLM 输出中的常见噪声格式。"""
    # 去除代码块标记
    text = re.sub(r"```[^\n]*\n?", "", text)
    # 去除常见前缀标签
    text = re.sub(
        r"^(Positive Prompt|Positive:|Prompt|OUTPUT|Result|Answer"
        r"|Here is[^:]*:|提示词|Output)[:\s]*",
        "", text, flags=re.IGNORECASE).strip()
    # 去除引号
    text = text.strip('"\'「」')
    # 合并多余空格
    text = re.sub(r"\s+", " ", text).strip()
    return text
