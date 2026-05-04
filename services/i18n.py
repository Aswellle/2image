"""
services/i18n.py — 多语言支持模块

架构说明：
- load_config() 在模块顶层调用，读取用户语言偏好
- 首次调用 load_locale() 后，所有 UI 使用 get_text(key) 获取翻译
- get_text() 找不到 key 时回退中文，不报错（向后兼容）
- UI 层通过 _t(key) 函数访问，当前实现为直接返回硬编码中文
  未来改造：app.py 中所有硬编码中文字符串 → _t("section.key")

使用方式：
    from services.i18n import get_text, set_locale
    get_text("img2img.generate_btn")   # → "🔄 图生图生成"
    set_locale("en_US")                 # 切换语言
"""
import json
import os
from typing import Optional

# 懒加载：配置和 locale 数据在首次调用时加载
_cfg: Optional[dict] = None
_cache: dict[str, dict] = {}       # lang_code -> locale_data
_current_lang: str = "zh_CN"       # 默认简体中文


def _get_locale_path(lang: str) -> str:
    base = os.path.dirname(__file__)
    return os.path.join(base, "locales", f"{lang}.json")


def _load_locale_data(lang: str) -> dict:
    """加载指定语言的 locale 文件，带缓存。"""
    if lang in _cache:
        return _cache[lang]
    path = _get_locale_path(lang)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _cache[lang] = data
            return data
        except Exception:
            pass
    # 找不到回退到中文
    if lang != "zh_CN":
        return _load_locale_data("zh_CN")
    return {}


def _init_from_config():
    """从 config 读取语言设置并加载对应 locale。"""
    global _current_lang
    try:
        from config.settings import load_config
        cfg = load_config()
        _current_lang = cfg.get("language", "zh_CN")
        _cfg = cfg
    except Exception:
        _current_lang = "zh_CN"
    _load_locale_data(_current_lang)


def get_text(key: str, default: Optional[str] = None) -> str:
    """
    获取翻译文本。

    参数：
        key     点分路径，如 "img2img.generate_btn"
        default 找不到时返回的默认值（None = 回退中文）

    查找逻辑：
        1. 尝试 _current_lang
        2. 找不到 → 回退 zh_CN
        3. 还找不到 → 返回 default 或 key 本身
    """
    if _cfg is None:
        _init_from_config()

    # 拆分 key：section.subsection.key
    parts = key.split(".")

    # 尝试当前语言
    data = _cache.get(_current_lang, {})
    for part in parts:
        if isinstance(data, dict) and part in data:
            data = data[part]
        else:
            data = None
            break

    if data is not None and isinstance(data, str):
        return data

    # 回退到中文
    if _current_lang != "zh_CN":
        data = _cache.get("zh_CN", {})
        for part in parts:
            if isinstance(data, dict) and part in data:
                data = data[part]
            else:
                data = None
                break
        if data is not None and isinstance(data, str):
            return data

    # 最后的兜底
    return default if default is not None else key


def format(key: str, **kwargs) -> str:
    """
    获取翻译文本并做 {placeholder} 插值。

    示例：
        format("app.success", provider="Pollinations", filename="img.png")
        # → "✓ Pollinations | 已保存：img.png"
    """
    return get_text(key).format(**kwargs)


def set_locale(lang: str) -> bool:
    """
    切换 UI 语言。
    返回是否切换成功。
    """
    global _current_lang
    if lang not in ("zh_CN", "en_US"):
        return False
    _load_locale_data(lang)
    _current_lang = lang

    # 持久化到配置
    try:
        from config.settings import load_config, save_config
        cfg = load_config()
        cfg["language"] = lang
        save_config(cfg)
    except Exception:
        pass
    return True


def current_locale() -> str:
    """返回当前语言代码。"""
    if _cfg is None:
        _init_from_config()
    return _current_lang


def available_locales() -> list[tuple[str, str]]:
    """返回可用语言列表 [(code, name), ...]"""
    return [
        ("zh_CN", "简体中文"),
        ("en_US", "English"),
    ]
