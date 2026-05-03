"""
services/providers/recraft.py
Recraft V3 — 状态：API 已下线（2025年官宣）

官方已关闭公共 API 访问（api.recraft.ai 所有端点返回 404）。
官方公告：https://recraft.ai/blog (搜索 API 相关更新)

如需类似功能，推荐替代方案：
- Ideogram V2（文字渲染质量最佳）→ try_ideogram
- Leonardo.ai（矢量风格 + img2img）→ try_leonardo
- OpenRouter Recraft 聚合端点（如未来重新上线）
"""
from typing import Callable, Tuple


def try_recraft(prompt, w, h, seed, cfg, log) -> Tuple[bytes, str]:
    """
    Recraft API 已于 2025 年关闭公共访问。
    此函数保留骨架，仅抛出明确错误，避免影响已有配置。
    如需矢量/插画风格，推荐使用 Ideogram V2 或 Leonardo.ai。
    """
    raise RuntimeError(
        "Recraft API 已下线（api.recraft.ai 返回 404）。"
        " 推荐替代：\n"
        "  - Ideogram V2（文字渲染天花板）：配置 ideogram_key\n"
        "  - Leonardo.ai（矢量风格+img2img）：配置 leonardo_key\n"
        " 详见：https://github.com/Aswellle/2image#%E8%AE%A1%E5%88%92%E6%8E%A5%E5%85%A5%E7%9A%84%E9%AB%98%E8%B4%A8%E9%87%8F-provider"
    )
