"""ui/ 层调色板护栏：裸色值冻结（ratchet）。

调色板的唯一事实来源是 config/theme.py（DARK_THEME）。UI 代码一律通过
C["token"] 引用；本测试冻结 ui/ 下允许残留的裸十六进制字面量清单——
只减不增：删除不受限，出现任何清单之外的新字面量即失败。

允许残留的仅限三类（新增功能请一律使用主题令牌）：
1. 数据可视化配色：热力图色阶、柱状分类色、排名奖牌色、KPI 着色卡、
   力度滑杆渐变端点（语义由 tests/test_strength_slider.py 锁定）；
2. 品牌/分类色：provider 章节品牌色、提示词模板与词库的分类色
   （与 config.theme.TAG_PALETTE 同性质的多色编码，不属于单一主题）；
3. 算法工具的黑白两极：对比度推导（button_states）与画布描边
   （canvas_image）需要的绝对黑白。
"""

import re
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

_HEX_LITERAL = re.compile(r'"#[0-9a-fA-F]{3,8}"')

ALLOWED = {
    # 力度滑杆渐变端点（数据可视化，语义被 test_strength_slider 引用）
    "#1d4ed8",
    "#7c3aed",
    "#dc2626",
    # ⊕ 按钮刻意的跨色按压反馈（绿）
    "#4ecca3",
    # 热力图色阶（stats_dashboard.HEAT）
    "#2d4270",
    "#0e3d2e",
    "#0a6647",
    "#0ea86e",
    "#a7f3d0",
    # 柱状分类色（stats_dashboard.BAR_COLORS）
    "#60a5fa",
    "#a78bfa",
    "#fb923c",
    "#f472b6",
    "#34d399",
    "#fbbf24",
    "#f87171",
    # 排名奖牌色（stats_dashboard.RANK_COLORS）
    "#f59e0b",
    "#94a3b8",
    "#b45309",
    "#475569",
    # KPI 着色卡（底色+亮字成对）
    "#0c2f5c",
    "#93c5fd",
    "#3b0764",
    "#c4b5fd",
    "#052e16",
    "#6ee7b7",
    "#451a03",
    "#fcd34d",
    "#1e1b4b",
    "#a5b4fc",
    # 热力格描边（比填充色略暗的派生边界）
    "#1e3560",
    # provider 章节品牌色（wizard_free / wizard_llm）
    "#ff6a00",
    "#d97706",
    "#8b5cf6",
    "#f97316",
    # 提示词模板分类色（prompt_wizard._CATEGORY_COLORS）
    "#be185d",
    "#1e40af",
    "#047857",
    "#7c2d12",
    "#0e7490",
    # 词库分类色（phrase_panel.CATEGORY_COLORS）
    "#92400e",
    "#0369a1",
    # 一次性状态面：LLM 隐私面板 / 预设选中态
    "#0d1f0d",
    "#1a4a1a",
    "#2e1f5c",
    # 算法工具黑白两极（button_states 对比度推导、canvas_image 描边）
    "#ffffff",
    "#000000",
}


def test_no_new_raw_hex_in_ui():
    found: dict[str, set[str]] = {}
    for path in sorted(UI_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for literal in _HEX_LITERAL.findall(text):
            found.setdefault(literal.lower().strip('"'), set()).add(path.name)
    extra = {hexv: sorted(files) for hexv, files in found.items() if hexv not in ALLOWED}
    assert not extra, f"ui/ 出现允许清单之外的裸色值（请改用 config/theme.py 令牌）: {extra}"


def test_allowed_list_stays_minimal():
    """允许清单不允许无谓膨胀：每个条目都应仍能在 ui/ 中找到。"""
    haystack = "\n".join(path.read_text(encoding="utf-8").lower() for path in UI_DIR.rglob("*.py"))
    unused = [hexv for hexv in sorted(ALLOWED) if f'"{hexv}"' not in haystack]
    assert not unused, f"允许清单中已无对应字面量的条目（请删除）: {unused}"
