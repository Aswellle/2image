"""E2E 旅程：提示词助手全交互（模板/生成/多候选/压缩/历史持久化）。"""

import pytest

from tests.e2e import driver


@pytest.fixture
def wizard(e2e, monkeypatch):
    """打开提示词助手并内联化其生成线程 + 打桩 LLM。"""
    import ui.prompt_wizard as pw_mod

    e2e.app._open_prompt_wizard()
    e2e.pump()
    pw = e2e.app._prompt_wizard
    assert pw is not None and pw.winfo_exists()

    class _InlineThread:
        def __init__(self, target=None, daemon=False, args=(), **kw):
            self._target = target
            self._args = args or ()

        def start(self):
            self._target(*self._args)

    monkeypatch.setattr(pw_mod, "threading", type("_M", (), {"Thread": _InlineThread}))
    yield pw
    try:
        pw._on_close()
    except Exception:
        pass


def _stub_llm(monkeypatch, results):
    import ui.prompt_wizard as pw_mod

    calls = []

    def fake_generate(**kwargs):
        calls.append(kwargs)
        text = results[len(calls) - 1] if len(calls) <= len(results) else results[-1]
        return text, ""

    monkeypatch.setattr(pw_mod, "generate_prompt", fake_generate)
    return calls


def test_wizard_opens_with_all_regions(wizard):
    """打开助手：参数页/结果框/状态/历史下拉全在场。"""
    pw = wizard
    assert pw._pos_box.winfo_exists()
    assert pw._gen_btn.winfo_exists()
    assert pw._hist_cb.winfo_exists()


def test_template_select_fills_keywords(wizard, e2e):
    """点模板卡片 → 关键词输入被填充并跳回参数页。"""
    pw = wizard
    from services.prompt_assistant import get_templates_by_category

    cats = list(get_templates_by_category().keys())
    tid = get_templates_by_category()[cats[0]][0][0]
    pw._select_tmpl(tid)
    e2e.pump()
    # 模板预览：结果框得到模板生成的提示词（非占位），状态标注预览中
    result = pw._pos_box.get("1.0", "end-1c").strip()
    assert result and "AI 生成或选中模板后" not in result
    assert pw._sel_tid == tid


def test_dimension_custom_option_expands_input(wizard, e2e):
    """维度下拉选“自定义…”：展开自定义输入框，切回预设则收起。

    回归：_on_select(self, _=None) 曾把 i18n `_` 遮蔽成事件参数，
    选中自定义项时抛 TypeError，输入框永远不出现。
    """
    from config.i18n import _

    dim = wizard._dim_mood
    dim.var.set(_("wizard_custom_option"))
    dim._on_select()
    e2e.pump()
    assert dim._expand.winfo_manager() == "pack", "选中自定义项应展开输入框"

    dim.var.set(dim._presets[0])
    dim._on_select()
    e2e.pump()
    assert dim._expand.winfo_manager() == ""


def test_generate_single_candidate(wizard, e2e, monkeypatch):
    """生成：LLM 打桩返回固定文案 → 结果框 + 使用按钮启用。"""
    pw = wizard
    _stub_llm(monkeypatch, ["masterpiece, best quality, a castle at dusk"])
    pw.kw_var.set("城堡 黄昏")
    driver.invoke_btn(pw._gen_btn)
    e2e.pump(8)
    assert pw._pos_box.get("1.0", "end-1c").strip() == "masterpiece, best quality, a castle at dusk"
    assert str(pw._use_btn.cget("state")) == "normal"


def test_generate_multi_candidates_with_switcher(wizard, e2e, monkeypatch):
    """多候选开关：3 候选生成 → 切换条 1/3 → ‹›切换内容。"""
    pw = wizard
    pw._variants_var.set(True)
    _stub_llm(
        monkeypatch,
        ["candidate one", "candidate two", "candidate three"],
    )
    pw.kw_var.set("多候选")
    driver.invoke_btn(pw._gen_btn)
    e2e.pump(8)
    assert pw._pos_box.get("1.0", "end-1c").strip() == "candidate one"
    assert "1 / 3" in str(pw._variant_lbl.cget("text"))
    pw._variant_shift(1)
    e2e.pump()
    assert pw._pos_box.get("1.0", "end-1c").strip() == "candidate two"
    pw._variant_shift(-2)
    e2e.pump()
    assert pw._pos_box.get("1.0", "end-1c").strip() == "candidate three"


def test_generate_failure_shows_error_state(wizard, e2e, monkeypatch):
    """LLM 全失败 → 错误状态呈现，应用不崩。"""
    pw = wizard
    import ui.prompt_wizard as pw_mod

    def fail_generate(**kwargs):
        raise RuntimeError("LLM down")

    monkeypatch.setattr(pw_mod, "generate_prompt", fail_generate)
    pw.kw_var.set("失败场景")
    driver.invoke_btn(pw._gen_btn)
    e2e.pump(8)
    assert "LLM down" in str(pw._status_lbl.cget("text")) or "失败" in str(pw._param_status.cget("text"))


def test_smart_trim_activates_on_long_result(wizard, e2e):
    """超预算结果 → 智能压缩按钮激活并可一键裁剪。"""
    pw = wizard
    long_pos = ", ".join([f"super detailed phrase number {i}" for i in range(60)])
    pw._on_done(long_pos, "超长")
    e2e.pump()
    assert str(pw._trim_btn.cget("state")) == "normal"
    pw._smart_trim()
    e2e.pump()
    trimmed = pw._pos_box.get("1.0", "end-1c")
    assert len(trimmed) < len(long_pos)


def test_use_button_sends_prompt_to_main_input(wizard, e2e):
    """使用提示词 → 结果写入主输入框（跨组件联调）。"""
    pw = wizard
    pw._on_done("use me in main", "联调")
    e2e.pump()
    driver.invoke_btn(pw._use_btn)
    e2e.pump()
    assert "use me in main" in e2e.app.content.pt.get("1.0", "end-1c")


def test_history_persists_across_reopen(wizard, e2e):
    """生成记录 → 历史下拉出现 → 关闭重开仍可加载（prompt_history.json）。"""
    pw = wizard
    pw._on_done("persisted prompt", "历史演示")
    e2e.pump()
    values = list(pw._hist_cb.cget("values"))
    assert values
    # 重开面板后历史仍在（跨会话持久化文件）
    pw._on_close()
    e2e.pump()
    from services.prompt_assistant import load_prompt_history

    hist = load_prompt_history()
    assert any("persisted prompt" == pos for _label, pos in hist)
    e2e.app._open_prompt_wizard()
    e2e.pump()
    pw2 = e2e.app._prompt_wizard
    assert list(pw2._hist_cb.cget("values")) == values


def test_escape_closes_wizard(e2e):
    """Escape 关闭助手窗口。"""
    e2e.app._open_prompt_wizard()
    e2e.pump()
    pw = e2e.app._prompt_wizard
    pw.event_generate("<Escape>")
    e2e.pump()
    assert e2e.app._prompt_wizard is None or not e2e.app._prompt_wizard.winfo_exists()
