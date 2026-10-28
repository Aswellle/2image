from unittest.mock import MagicMock, patch

from ui.prompt_wizard import PromptWizard


class DummyWidget:
    def __init__(self, text=""):
        self.options = {"text": text}
        self.deleted = []
        self.inserted = []

    def config(self, **kwargs):
        self.options.update(kwargs)

    def get(self, *_args):
        return self.options["text"]

    def delete(self, *args):
        self.deleted.append(args)

    def insert(self, *args):
        self.inserted.append(args)

    def cget(self, key):
        return self.options.get(key, "")


def make_wizard():
    wizard = PromptWizard.__new__(PromptWizard)
    wizard._template_badge = DummyWidget()
    wizard._tmpl_apply_btn = DummyWidget()
    wizard._fill_btn = DummyWidget()
    wizard._use_btn = DummyWidget()
    wizard._clear_btn = DummyWidget()
    return wizard


def test_template_state_gates_actions_until_application():
    wizard = make_wizard()

    wizard._set_template_state(PromptWizard._TEMPLATE_IDLE)
    assert wizard._template_badge.options["text"] == "● 空闲"
    assert wizard._tmpl_apply_btn.options["state"] == "disabled"
    assert wizard._fill_btn.options["state"] == "disabled"
    assert wizard._use_btn.options["state"] == "disabled"
    assert wizard._clear_btn.options["state"] == "disabled"

    wizard._set_template_state(PromptWizard._TEMPLATE_PREVIEWING)
    assert wizard._template_badge.options["text"] == "◐ 预览中"
    assert wizard._tmpl_apply_btn.options["state"] == "normal"
    assert wizard._fill_btn.options["state"] == "disabled"
    assert wizard._use_btn.options["state"] == "disabled"
    assert wizard._clear_btn.options["state"] == "disabled"

    wizard._set_template_state(PromptWizard._TEMPLATE_PENDING_FILL)
    assert wizard._template_badge.options["text"] == "● 待填充"
    assert wizard._tmpl_apply_btn.options["state"] == "disabled"
    assert wizard._fill_btn.options["state"] == "normal"
    assert wizard._use_btn.options["state"] == "normal"
    assert wizard._clear_btn.options["state"] == "normal"


def test_apply_template_promotes_preview_to_pending_fill():
    wizard = make_wizard()
    wizard._template_state = PromptWizard._TEMPLATE_PREVIEWING
    wizard._sel_tid = "xhs_hot"
    wizard.tmpl_kw_var = DummyWidget("咖啡")
    wizard._tmpl_status = DummyWidget()
    # _apply_template 经真实 _on_done 落到待填充态
    wizard._anim_id = None
    wizard._gen_btn = DummyWidget()
    wizard._param_status = DummyWidget()
    wizard._status_lbl = DummyWidget()
    wizard.after = lambda *_args: None
    wizard._pos_box = DummyWidget()
    wizard._update_budget_display = lambda: None
    wizard._history = []
    wizard._hist_cb = DummyWidget()
    wizard.app = MagicMock()

    with patch("ui.prompt_wizard.apply_template", return_value=("positive", "ignored")):
        wizard._apply_template()

    assert wizard._pos_box.inserted == [("1.0", "positive")]
    assert wizard._template_state == PromptWizard._TEMPLATE_PENDING_FILL
    assert wizard._use_btn.options["state"] == "normal"


def test_clear_template_content_removes_the_prompt():
    wizard = make_wizard()
    wizard._template_state = PromptWizard._TEMPLATE_PENDING_FILL
    wizard._pos_box = DummyWidget("applied prompt")
    wizard._status_lbl = DummyWidget()
    wizard.after = lambda *_args: None
    wizard._budget_lbl = DummyWidget()
    wizard._trim_btn = DummyWidget()
    wizard._tmpl_status = DummyWidget("已应用：模板")

    wizard._clear_template_content()

    assert wizard._pos_box.deleted == [("1.0", "end")]
    assert wizard._template_badge.options["text"] == "● 空闲"
    assert wizard._use_btn.options["state"] == "disabled"
    assert wizard._clear_btn.options["state"] == "disabled"
    assert wizard._tmpl_status.options["text"] == ""


def test_use_prompt_returns_template_flow_to_idle():
    wizard = make_wizard()
    wizard._template_state = PromptWizard._TEMPLATE_PENDING_FILL
    wizard._pos_box = DummyWidget("applied prompt")
    wizard._status_lbl = DummyWidget()
    wizard.after = lambda *_args: None
    wizard.app = MagicMock()
    wizard.app.pt = DummyWidget()
    wizard.app.root = MagicMock()
    wizard.app.pt.options["bg"] = "#000000"

    wizard._use_prompt()

    assert wizard.app.pt.inserted == [("1.0", "applied prompt")]
    assert wizard._template_state == PromptWizard._TEMPLATE_IDLE
    assert wizard._use_btn.options["state"] == "disabled"
    assert wizard._clear_btn.options["state"] == "disabled"


def _make_result_ready_wizard():
    wizard = make_wizard()
    wizard._anim_id = None
    wizard._gen_btn = DummyWidget()
    wizard._param_status = DummyWidget()
    wizard._status_lbl = DummyWidget()
    wizard.after = lambda *_args: None
    wizard._pos_box = DummyWidget()
    wizard._update_budget_display = lambda: None
    wizard._history = []
    wizard._hist_cb = DummyWidget()
    wizard.app = MagicMock()
    return wizard


def test_param_generation_result_enables_use_and_fill():
    """参数模式 AI 生成完成必须落在待填充态 —— 此前落在 idle，
    导致最常用的"生成 → 使用"主路径中两个按钮永远禁用。"""
    wizard = _make_result_ready_wizard()

    wizard._on_done("a beautiful castle", "关键词: castle")

    assert wizard._template_state == PromptWizard._TEMPLATE_PENDING_FILL
    assert wizard._use_btn.options["state"] == "normal"
    assert wizard._fill_btn.options["state"] == "normal"
    assert wizard._pos_box.inserted == [("1.0", "a beautiful castle")]


def test_history_reload_enables_use():
    """会话历史回载的结果同样必须可使用/可填充。"""
    wizard = _make_result_ready_wizard()
    wizard._history = [("关键词: castle", "a beautiful castle")]
    wizard._hist_cb.current = lambda *_args: 0

    wizard._load_history()

    assert wizard._template_state == PromptWizard._TEMPLATE_PENDING_FILL
    assert wizard._use_btn.options["state"] == "normal"
