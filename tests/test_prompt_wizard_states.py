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
    wizard.app = MagicMock()
    wizard._on_done = MagicMock()
    wizard._tmpl_status = DummyWidget()

    with patch("ui.prompt_wizard.apply_template", return_value=("positive", "ignored")):
        wizard._apply_template()

    wizard._on_done.assert_called_once_with("positive", "[模板] 🌸 小红书爆款封面")
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
