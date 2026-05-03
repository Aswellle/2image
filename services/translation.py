"""
services/translation.py — 中译英
"""
import re


def has_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def translate_zh_to_en(text: str) -> str:
    """
    简单的中文→英文翻译占位。
    实际使用时可接入 Google Translate API、DeepSeek 或其他翻译服务。
    这里直接返回原文，因为大多数图像生成模型接受中英文混合输入。
    """
    return text
