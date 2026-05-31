"""
services/phrase_library.py  v2
───────────────────────────────
提示词片段库：内置 45 条预设 + 用户自定义词条（持久化到 JSON）

v2 新增：
  PHRASE_DESCRIPTIONS  ── 每条内置词条的中文效果说明
  get_phrase_desc()    ── 按词条查询中文说明，供 phrase_panel 悬浮提示使用
"""
import json
import os
from config.settings import APP_DIR

_CUSTOM_FILE = os.path.join(APP_DIR, "phrase_library.json")

# ── 内置 45 条预设（7 大分类）─────────────────────────────────
BUILTIN_PHRASES: dict[str, list[str]] = {
    "✨ 画质增强": [
        "masterpiece",
        "best quality",
        "ultra-detailed",
        "8K UHD",
        "HDR",
        "RAW photo",
        "sharp focus",
        "professional photography",
    ],
    "💡 光影效果": [
        "golden hour lighting",
        "volumetric light rays",
        "Rembrandt lighting",
        "neon night lighting",
        "soft natural window light",
        "backlit silhouette",
        "cinematic dramatic lighting",
    ],
    "🎨 艺术风格": [
        "photorealistic",
        "oil painting style",
        "watercolor illustration",
        "anime style",
        "cyberpunk aesthetic",
        "vintage film grain",
        "3D octane render",
    ],
    "📐 构图方式": [
        "rule of thirds",
        "centered symmetrical composition",
        "wide establishing shot",
        "extreme close-up",
        "bird's eye view",
        "low angle worm's eye view",
    ],
    "📷 镜头参数": [
        "85mm portrait lens, f/1.4 bokeh",
        "35mm street photography",
        "24mm wide angle, f/4",
        "macro lens extreme close-up",
        "fisheye 180° distortion",
        "telephoto 200mm compression",
    ],
    "🌙 氛围情绪": [
        "romantic dreamy atmosphere",
        "mysterious dark mood",
        "epic cinematic scale",
        "warm cozy feeling",
        "melancholic solitary tone",
        "cheerful vibrant energy",
    ],
    "👤 人物细节": [
        "smooth porcelain skin",
        "ultra-detailed hair strands",
        "fabric texture detail",
        "expressive detailed eyes",
        "natural minimal makeup",
    ],
}

ALL_CATEGORIES: list[str] = list(BUILTIN_PHRASES.keys())

# ──────────────────────────────────────────────────────────────
#   词条中文说明字典（用于 phrase_panel 悬浮提示）
#   每条 60～100 字，突出「可见的画面效果」而非学术定义
# ──────────────────────────────────────────────────────────────
PHRASE_DESCRIPTIONS: dict[str, str] = {

    # ─── ✨ 画质增强 ──────────────────────────────────────────
    "masterpiece": (
        "🏆 最高画质总指令。让模型向博物馆级艺术品看齐，"
        "整体精细度与构图美感大幅提升。几乎适用所有场景，"
        "是使用频率最高的质量提升词，建议每次生成都加上。"
    ),
    "best quality": (
        "🌟 「最佳质量」通用提升词。显著减少模糊与瑕疵，"
        "提高细节渲染优先级。常与 masterpiece 搭配使用，"
        "双重强化画面品质，两者叠加效果更明显。"
    ),
    "ultra-detailed": (
        "🔬 「超高细节」。皮肤纹理、布料编织、树叶脉络等"
        "微观细节更加丰富细腻，让图像经得起放大审视。"
        "追求精致感的人像、静物场景的首选提升词。"
    ),
    "8K UHD": (
        "📺 模拟 8K 超高清分辨率画质。画面锐度与信息量大幅"
        "提升，常与 masterpiece 连用进一步强化细节。"
        "适合需要大尺寸展示或印刷输出的图像场景。"
    ),
    "HDR": (
        "🌈 高动态范围（High Dynamic Range）。增强亮部与暗部"
        "层次对比，颜色更饱满鲜艳，对比更强烈。"
        "尤其适合光线复杂的风景与建筑题材，防止过曝失真。"
    ),
    "RAW photo": (
        "📷 模拟相机 RAW 原始格式直出效果。质感真实自然，"
        "无过度后期调色感，还原真实生活质感。"
        "适合纪实摄影风格、强调真实感的人像与街头场景。"
    ),
    "sharp focus": (
        "🎯 「锐利对焦」。主体边缘清晰分明，消除软焦模糊感。"
        "与浅景深（bokeh）配合使用效果最佳：主体锐利，"
        "背景柔化。适合人像特写与产品摄影。"
    ),
    "professional photography": (
        "📸 「专业摄影」级别。照明设计与构图达到商业摄影水准，"
        "整体质感如同杂志大片。"
        "适合需要广告图或时尚写真感的高品质图像。"
    ),

    # ─── 💡 光影效果 ──────────────────────────────────────────
    "golden hour lighting": (
        "🌅 「黄金时段光」。日出后或日落前约一小时的暖橙色"
        "低角度自然光，光线柔和且富有方向感。"
        "是人像与风景摄影最受追捧的自然光效，浪漫氛围感极强。"
    ),
    "volumetric light rays": (
        "✨ 「体积光」（丁达尔效应）。光线穿透烟雾或树叶缝隙"
        "时产生的可见光柱，神圣感与戏剧感强烈。"
        "常见于森林晨光、教堂彩窗光等场景，视觉冲击力极大。"
    ),
    "Rembrandt lighting": (
        "🎨 17世纪荷兰画家的经典布光法。脸颊一侧形成三角形"
        "亮斑，另侧进入阴影，对比鲜明、立体感强。"
        "是肖像摄影与艺术人像的经典用光技法，高级感十足。"
    ),
    "neon night lighting": (
        "🔮 「霓虹夜光」。赛博朋克风的彩色霓虹灯光在人物与"
        "建筑上形成蓝/粉/绿色鲜艳色彩投影，科幻感十足。"
        "适合都市夜景、赛博朋克人像等现代感主题。"
    ),
    "soft natural window light": (
        "🪟 「柔和自然窗光」。从窗口漫射进来的散射光，均匀"
        "无硬阴影，皮肤质感细腻通透。是日系摄影和室内人像"
        "的经典光源，还原生活真实感与亲切感的首选。"
    ),
    "backlit silhouette": (
        "🌇 「逆光剪影」。主体轮廓清晰而内部为暗色，背景产生"
        "光晕（Flare），文艺感与戏剧感十足。"
        "适合落日海边、逆光树林等富有诗意的场景。"
    ),
    "cinematic dramatic lighting": (
        "🎬 「电影级戏剧光效」。强对比的高光与深暗阴影，模拟"
        "好莱坞大片的布光风格，为画面注入强烈视觉张力。"
        "适合英雄、悬疑、史诗等视觉冲击力强的题材。"
    ),

    # ─── 🎨 艺术风格 ──────────────────────────────────────────
    "photorealistic": (
        "📸 「照片级写实」。高度逼真，细节与质感与真实照片"
        "几乎难以区分。适合需要超现实感或以假乱真效果，"
        "是写实人像、产品展示的核心风格词。"
    ),
    "oil painting style": (
        "🖼 「油画风格」。模拟传统油画的厚重笔触感、丰富色层"
        "叠加与古典质感，历史感与艺术感并重。"
        "适合肖像、风景等具有欧洲古典艺术氛围的主题。"
    ),
    "watercolor illustration": (
        "🎨 「水彩插画」。半透明色彩晕染、边缘柔和自然、"
        "隐约纸纹感，风格温柔清新。适合儿童读物封面、"
        "情感类插图与轻松愉快的主题。"
    ),
    "anime style": (
        "✨ 「日本动漫风格」。大眼睛、细腻线条、明快色彩，"
        "适合二次元角色设计、轻小说封面、游戏角色立绘。"
        "注意：与写实词同用会相互冲突，建议单独使用。"
    ),
    "cyberpunk aesthetic": (
        "🤖 「赛博朋克美学」。霓虹灯与黑暗对比、科技感改造"
        "与反乌托邦都市背景。常见于未来都市夜景、"
        "机械义肢人、数字朋克等科幻主题。"
    ),
    "vintage film grain": (
        "📽 「复古胶片颗粒」。模拟上世纪胶卷的噪点感与特有"
        "色调偏移（偏黄绿），营造强烈怀旧感与年代感。"
        "适合复古主题，让图像像珍贵的老照片般充满故事感。"
    ),
    "3D octane render": (
        "💻 「Octane 3D 渲染」。基于物理光线追踪，玻璃折射、"
        "金属高光、皮肤次表面散射效果极为真实细腻。"
        "适合产品可视化、科幻场景与概念设计图。"
    ),

    # ─── 📐 构图方式 ──────────────────────────────────────────
    "rule of thirds": (
        "📐 「三分构图法」。将画面分成九宫格，主体置于交叉点，"
        "视觉平衡而富有动感。摄影最基础也最实用的构图原则，"
        "适合绝大多数场景，让画面自然好看而不显呆板。"
    ),
    "centered symmetrical composition": (
        "⚖ 「中心对称构图」。主体居于正中，左右完全对称，"
        "庄重、权威且视觉冲击力强，极具仪式感。"
        "适合建筑门廊、正面人像、LOGO类图像。"
    ),
    "wide establishing shot": (
        "🌄 「宽景定场镜头」。展示大范围环境与空间比例关系，"
        "赋予画面宏大叙事感与史诗气质。适合奇幻世界、"
        "影视剧开场或自然风光的全景展示。"
    ),
    "extreme close-up": (
        "🔍 「极端特写」。聚焦极小范围（眼球、嘴唇、指尖），"
        "视觉冲击力极强，让观者感受到强烈临近感。"
        "常用于悬疑类或需要强调细节情绪张力的图像。"
    ),
    "bird's eye view": (
        "🐦 「鸟瞰俯视角度」。从正上方向下俯视，展示整体布局"
        "与几何图案，视角独特新颖、构图感强。"
        "适合城市俯瞰、餐食摆拍、大型集会等宏观场景。"
    ),
    "low angle worm's eye view": (
        "🐛 「仰视蚯蚓视角」。从极低处向上仰视，使主体显得"
        "高大雄伟、充满压迫感与力量感。"
        "适合英雄形象塑造、摩天高楼与纪念碑类构图。"
    ),

    # ─── 📷 镜头参数 ──────────────────────────────────────────
    "85mm portrait lens, f/1.4 bokeh": (
        "📸 人像黄金焦段 + 超大光圈。浅景深令背景呈现奶油般"
        "柔化（Bokeh），主体与背景分离感极佳，背景虚化超美。"
        "是专业人像摄影最受欢迎的镜头参数组合。"
    ),
    "35mm street photography": (
        "🚶 35mm 广角小焦段，视角接近人眼自然视野，环境代入"
        "感强。保留人物的同时保留生动的生活场景，真实感强。"
        "适合街头纪实、城市生活类图像。"
    ),
    "24mm wide angle, f/4": (
        "🌐 超广角焦段，视角约 84°，强烈的透视感与夸张的空间"
        "纵深效果。适合风景与建筑摄影，"
        "能最大程度呈现大场景的宏大气势。"
    ),
    "macro lens extreme close-up": (
        "🔬 「微距镜头特写」。将微小物体放大数倍，呈现肉眼"
        "难以察觉的细节（花蕊、昆虫复眼、水滴倒影）。"
        "视觉震撼，科普摄影与微观世界展示必备词。"
    ),
    "fisheye 180° distortion": (
        "🐟 「鱼眼镜头」。180° 超广视角配合强烈球面畸变，"
        "画面四周明显弯曲变形，视觉效果夸张独特。"
        "常见于极限运动第一视角、全景球形摄影与艺术创作。"
    ),
    "telephoto 200mm compression": (
        "🔭 200mm 长焦镜头。前后景在视觉上被「压缩」叠加，"
        "产生背景与前景贴近的空间压缩感。"
        "适合野生动物、远处人像及层叠山峦等远摄场景。"
    ),

    # ─── 🌙 氛围情绪 ──────────────────────────────────────────
    "romantic dreamy atmosphere": (
        "💕 「浪漫梦幻氛围」。柔焦光晕、飘落花瓣、粉紫梦幻"
        "色调，营造甜美爱恋、如梦似幻的温柔感。"
        "适合情侣写真、花语主题、少女风格图像。"
    ),
    "mysterious dark mood": (
        "🌑 「神秘黑暗情绪」。低调暗部、冷蓝黑色调阴影、"
        "隐约若现的轮廓，营造悬疑、哥特风格的神秘压抑感。"
        "适合惊悚、奇幻、哲学主题的图像创作。"
    ),
    "epic cinematic scale": (
        "🎬 「史诗电影尺度」。宏大视野、壮观光效与开阔构图，"
        "给人荡气回肠的叙事感，如同大制作电影海报。"
        "适合奇幻、历史战争、科幻星际等宏大主题图像。"
    ),
    "warm cozy feeling": (
        "🕯 「温暖舒适感」。暖黄橙色调、居家陈设、柔和台灯或"
        "壁炉灯光，传递安全感与慵懒惬意感。"
        "适合生活方式类图像，让人感到放松与归属感。"
    ),
    "melancholic solitary tone": (
        "🌧 「忧郁孤独基调」。冷蓝灰色调、空旷构图、"
        "孤独人物的背影或仰望空旷天空，带有淡淡哀愁。"
        "适合文学艺术类主题图像，诗意的孤独美感。"
    ),
    "cheerful vibrant energy": (
        "☀ 「欢快活力感」。鲜艳高饱和色彩、动态姿势、"
        "阳光明媚的高亮场景，充满青春朝气与正能量。"
        "适合青少年、运动、节日庆典类图像。"
    ),

    # ─── 👤 人物细节 ──────────────────────────────────────────
    "smooth porcelain skin": (
        "✨ 「如瓷器般光滑肌肤」。细腻白皙、几乎无瑕疵的"
        "完美皮肤质感，是美妆广告、时尚写真与商业人像"
        "中使用频率最高的肤质描述词。"
    ),
    "ultra-detailed hair strands": (
        "💇 「超细腻发丝」。每根头发纹理清晰可辨，层次感与"
        "飘动感自然真实，大幅提升整体精致感。"
        "适合需要精细头发表现的人像特写场景。"
    ),
    "fabric texture detail": (
        "👗 「布料纹理细节」。精准还原丝绸光泽、棉麻粗糙感、"
        "皮革纹路或针织网孔等面料质感。"
        "大幅提升服饰画面的真实感与品质感，适合时装类图像。"
    ),
    "expressive detailed eyes": (
        "👁 「富有表情的细节眼睛」。瞳孔纹路、睫毛层次与"
        "高光点清晰细腻，让人物眼神充满情感张力。"
        "是人物「灵魂之窗」最重要的细节词，大幅提升气质。"
    ),
    "natural minimal makeup": (
        "💋 「自然裸妆效果」。轻薄底妆、保留皮肤原有质地，"
        "追求清新素颜感，让人物看起来真实不过度美化。"
        "适合日系或纪实风格的人像，更有亲和力与真实感。"
    ),
}


# ── 用户自定义词条 ────────────────────────────────────────────
def _load_custom() -> dict[str, list[str]]:
    try:
        if os.path.exists(_CUSTOM_FILE):
            return json.load(open(_CUSTOM_FILE, "r", encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_custom(data: dict) -> None:
    json.dump(data, open(_CUSTOM_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def get_all_phrases() -> dict[str, list[str]]:
    """合并内置 + 用户自定义，返回完整词库。"""
    merged = {k: list(v) for k, v in BUILTIN_PHRASES.items()}
    custom = _load_custom()
    for cat, phrases in custom.items():
        if cat in merged:
            for p in phrases:
                if p not in merged[cat]:
                    merged[cat].append(p)
        else:
            merged[cat] = list(phrases)
    return merged


def get_phrase_desc(phrase: str) -> str:
    """返回指定词条的中文效果说明，无内置说明时返回空字符串。"""
    return PHRASE_DESCRIPTIONS.get(phrase, "")


def add_custom_phrase(category: str, phrase: str) -> None:
    data = _load_custom()
    if category not in data:
        data[category] = []
    phrase = phrase.strip()
    if phrase and phrase not in data[category]:
        data[category].append(phrase)
    _save_custom(data)


def delete_custom_phrase(category: str, phrase: str) -> None:
    data = _load_custom()
    if category in data and phrase in data[category]:
        data[category].remove(phrase)
        if not data[category]:
            del data[category]
        _save_custom(data)


def is_builtin(category: str, phrase: str) -> bool:
    return phrase in BUILTIN_PHRASES.get(category, [])
