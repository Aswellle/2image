"""E2E 回归：二次确认对话框、模态性、热力图空态样式、向导占位标签。"""

import tkinter as tk

from config.theme import C
from data import repository
from data.repository import add_entry, count_entries


def _insert_old_entry(timestamp: str = "2000-01-01 10:00:00") -> None:
    """直接插一条远古记录：让当前年（含今天）保持无数据。"""
    conn = repository._conn()
    conn.execute(
        "INSERT INTO history(timestamp,prompt,translated,image_path,provider,nickname,favorited,tags)"
        " VALUES (?,?,?,?,?,NULL,0,'')",
        (timestamp, "old prompt", "", "old.png", "Pollinations/flux"),
    )
    conn.commit()


def _walk(w, cls):
    for ch in w.winfo_children():
        if isinstance(ch, cls):
            yield ch
        yield from _walk(ch, cls)


# ══════════ 侧栏重置 / 清空历史：二次确认 ══════════
def test_reset_asks_confirmation_then_clears_view_state(e2e):
    """重置：先弹确认；确认后清空筛选/草稿，历史记录不受影响。"""
    add_entry("keep me", "", "a.png", "Pollinations/flux")
    e2e.app._refresh_hist()
    e2e.pump()
    e2e.app.sidebar._fav_only = True
    e2e.set_prompt("draft prompt to clear")

    e2e.app._reset_view()
    e2e.pump()

    assert "askyesno" in e2e.dialog_kinds(), "重置必须弹二次确认"
    assert e2e.app.sidebar._fav_only is False
    assert e2e.app.content.pt.get("1.0", "end-1c").strip() == ""
    assert count_entries() == 1, "重置视图不得删除历史记录"


def test_reset_cancel_keeps_everything(e2e, monkeypatch):
    """重置取消：草稿与筛选保持原样。"""
    import tkinter.messagebox as mb

    e2e.app.sidebar._fav_only = True
    e2e.set_prompt("keep my draft")
    monkeypatch.setattr(mb, "askyesno", lambda *a, **k: False)

    e2e.app._reset_view()
    e2e.pump()

    assert "keep my draft" in e2e.app.content.pt.get("1.0", "end-1c")
    assert e2e.app.sidebar._fav_only is True


def test_clear_history_asks_confirmation_then_clears(e2e):
    """清空历史：先弹确认；确认后记录清零。"""
    add_entry("p1", "", "a.png", "Pollinations/flux")
    add_entry("p2", "", "b.png", "Pollinations/flux")
    e2e.app._refresh_hist()
    e2e.pump()

    e2e.app.sidebar._clear_hist()
    e2e.pump()

    assert "askyesno" in e2e.dialog_kinds(), "清空历史必须弹二次确认"
    assert count_entries() == 0


def test_clear_history_cancel_keeps_records(e2e, monkeypatch):
    """清空历史取消：记录全部保留。"""
    import tkinter.messagebox as mb

    add_entry("p1", "", "a.png", "Pollinations/flux")
    monkeypatch.setattr(mb, "askyesno", lambda *a, **k: False)

    e2e.app.sidebar._clear_hist()
    e2e.pump()

    assert count_entries() == 1


# ══════════ 自定义对话框：模态 grab + transient（点击外部不可关闭） ══════════
def test_tag_editor_dialog_is_modal_and_owned(e2e):
    """标签编辑对话框：持有 grab（点击外部不可操作/关闭）且归属主窗。"""
    entry = add_entry("tagged", "", "a.png", "Pollinations/flux")
    e2e.app._refresh_hist()
    e2e.pump()

    e2e.app.sidebar._open_tag_editor(entry)
    e2e.pump()

    grabs = [w for w in _walk(e2e.app.root, tk.Toplevel) if w.grab_current() is w]
    assert grabs, "标签编辑对话框应持有 grab_set（模态）"
    dlg = grabs[-1]
    assert str(dlg.transient()), "对话框应设置 transient 归属主窗"
    dlg.destroy()
    e2e.pump()


def test_phrase_vars_dialog_is_modal_and_owned(e2e):
    """模板变量填充对话框：grab + transient。"""
    from services import phrase_library as pl

    pl.add_custom_phrase("✨ 画质增强", "{{subject}} at {{place}}")
    e2e.app._open_phrase_panel()
    e2e.pump()
    pp = e2e.app._phrase_panel

    pp._append_to_input("{{subject}} at {{place}}")
    e2e.pump()

    dialogs = [w for w in pp.winfo_children() if isinstance(w, tk.Toplevel)]
    assert dialogs, "变量填充对话框应出现"
    dlg = dialogs[-1]
    assert dlg.grab_current() is dlg, "变量填充对话框必须模态（grab）"
    assert str(dlg.transient()), "变量填充对话框应归属词库面板"
    dlg.destroy()


# ══════════ 热力图：空数据格子不得有装饰性描边 ══════════
def test_heatmap_empty_cells_have_no_purple_today_ring(e2e):
    """今天无数据时，今日格子保持普通空格样式（历史紫框属样式污染）。"""
    _insert_old_entry()  # 当前年（含今天）无数据 → 今日格必为空格
    e2e.app._show_stats()
    e2e.pump()
    sd = e2e.app._stats_win

    def _cell_canvas():
        for cv in _walk(sd.win, tk.Canvas):
            if cv.find_withtag("cell"):
                return cv
        return None

    assert e2e.wait_until(lambda: _cell_canvas() is not None, timeout_ms=5000), "热力图未绘制"
    cv = _cell_canvas()
    empty_outlines = set()
    for it in cv.find_withtag("cell"):
        if cv.itemcget(it, "fill") == "#2d4270":  # HEAT[0] 空数据底色
            empty_outlines.add(cv.itemcget(it, "outline"))
    assert C["purple"] not in empty_outlines, "空数据格子不应出现今日紫描边"

    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        sd.win.unbind_all(seq)
    sd.win.destroy()


def test_heatmap_today_with_data_still_marked(e2e):
    """今天有数据时保留今日紫描边（对比度提示：标记只随数据出现）。"""
    add_entry("today data", "", "a.png", "Pollinations/flux")
    e2e.app._show_stats()
    e2e.pump()
    sd = e2e.app._stats_win

    def _cell_canvas():
        for cv in _walk(sd.win, tk.Canvas):
            if cv.find_withtag("cell"):
                return cv
        return None

    assert e2e.wait_until(lambda: _cell_canvas() is not None, timeout_ms=5000)
    cv = _cell_canvas()
    rings = [it for it in cv.find_withtag("cell") if cv.itemcget(it, "outline") == C["purple"]]
    assert rings, "今日有数据时应保留紫描边标记"

    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        sd.win.unbind_all(seq)
    sd.win.destroy()


# ══════════ 配置向导：空白占位标签不得露出默认底色 ══════════
def _assert_no_opaque_spacers(win, label: str) -> None:
    bad = []
    for lbl in _walk(win, tk.Label):
        if str(lbl.cget("text")) != "":
            continue
        try:
            if str(lbl.cget("bg")) != str(lbl.master.cget("bg")):
                bad.append((str(lbl), str(lbl.cget("bg")), str(lbl.master.cget("bg"))))
        except tk.TclError:
            pass
    assert not bad, f"{label}: 发现默认底色的空白占位标签（白色竖条）: {bad[:3]}"


def test_wizard_spacer_labels_are_transparent(e2e):
    """供应商信息卡内的空文本标签必须与父容器同底色（否则渲染成白色竖条）。"""
    e2e.app._open_wizard()
    e2e.pump()
    wiz = e2e.app._free_wizard
    assert wiz is not None and wiz.winfo_exists()
    _assert_no_opaque_spacers(wiz, "免费配置向导")
    wiz.destroy()


def test_paid_wizard_spacer_labels_are_transparent(e2e):
    """付费配置向导同样不得出现白色竖条占位。"""
    e2e.app._open_paid_wizard()
    e2e.pump()
    wiz = e2e.app._paid_wizard
    assert wiz is not None and wiz.winfo_exists()
    _assert_no_opaque_spacers(wiz, "付费配置向导")
    wiz.destroy()


def test_llm_wizard_spacer_labels_are_transparent(e2e):
    """提示词助手模型配置向导同样不得出现白色竖条占位。"""
    e2e.app._open_prompt_wizard()
    e2e.pump()
    pw = e2e.app._prompt_wizard
    pw._open_llm_wizard()
    e2e.pump()
    from ui.wizard_llm import LLMWizard

    dlg = [w for w in _walk(pw, tk.Toplevel) if isinstance(w, LLMWizard)]
    assert dlg, "LLM 配置向导应打开"
    _assert_no_opaque_spacers(dlg[-1], "LLM 配置向导")
    dlg[-1].destroy()
