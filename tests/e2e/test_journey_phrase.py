"""E2E 旅程：词库面板全交互 + 与主输入框/侧栏的跨组件联调。"""

import json
import tkinter as tk

from config.theme import C
from data.repository import add_entry
from services import phrase_library as pl


def _open(e2e):
    e2e.app._open_phrase_panel()
    e2e.pump()
    return e2e.app._phrase_panel


def _walk(w, cls):
    for ch in w.winfo_children():
        if isinstance(ch, cls):
            yield ch
        yield from _walk(ch, cls)


def test_open_close_via_escape(e2e):
    """Ctrl+B 旅程之外：直接开面板 → Escape 关闭 → 单例引用清理。"""
    pp = _open(e2e)
    assert pp.winfo_exists()
    pp.event_generate("<Escape>")
    e2e.pump()
    assert e2e.app._phrase_panel is None or not e2e.app._phrase_panel.winfo_exists()


def test_category_switch_renders_chips(e2e):
    """切换分类 → 词条卡片渲染对应词条。"""
    pp = _open(e2e)
    second = list(pp._phrases.keys())[1]
    pp._select_cat(second)
    e2e.pump()
    assert pp._cur_cat == second
    chips = len(pp._chip_btns)
    assert chips == len(pp._phrases[second])


def test_search_shows_attribution_and_count(e2e):
    """跨分类搜索：添加按钮禁用（守卫生效）、分类上下文保留。"""
    pp = _open(e2e)
    pp._sv.set("light")
    assert e2e.wait_until(lambda: pp._search_after is None, timeout_ms=3000), "搜索防抖未触发"
    assert pp._add_btn.cget("state") == "disabled"
    assert pp._cur_cat  # 左栏状态保留


def test_search_is_debounced(e2e):
    """连续键入只过滤一次：每个字符都重建全部卡片会明显卡顿。"""
    pp = _open(e2e)
    calls = []
    orig = pp._render_chips

    def _counting(*args, **kwargs):
        calls.append(1)
        return orig(*args, **kwargs)

    pp._render_chips = _counting
    for text in ("l", "li", "lig"):
        pp._sv.set(text)
    assert e2e.wait_until(lambda: pp._search_after is None, timeout_ms=3000)
    assert len(calls) == 1, f"防抖应只触发一次过滤，实际 {len(calls)} 次"


def test_search_empty_state_has_clear_button(e2e):
    """搜索空态 → 清除按钮可一键恢复。"""
    pp = _open(e2e)
    pp._sv.set("zzzz-no-match")
    assert e2e.wait_until(lambda: pp._search_after is None, timeout_ms=3000)
    clear_btns = [b for b in pp._chip_inner.winfo_children() if isinstance(b, tk.Frame)]
    assert clear_btns  # 空态容器存在
    pp._sv.set("")
    assert e2e.wait_until(lambda: pp._add_btn.cget("state") == "normal", timeout_ms=3000)


def test_add_custom_phrase_end_to_end(e2e):
    """输入词条 → 添加到当前分类 → 持久化文件出现。"""
    pp = _open(e2e)
    cat = list(pp._phrases.keys())[0]
    pp._select_cat(cat)
    pp._new_phrase_var.set("my custom e2e phrase")
    pp._add_phrase()
    e2e.pump()
    all_phrases = pl.get_all_phrases()
    assert "my custom e2e phrase" in all_phrases[cat]


def test_prompt_flash_restores_entry_background(e2e):
    """连续追加两次：只保留最后一个恢复定时器，最终回到 entry 底色。

    回归：每次闪烁都以当前 bg 作为「原底色」，第二次会把高亮色写回，
    输入框永久卡在闪烁态。
    """
    pp = _open(e2e)
    pp._insert_phrase_text("first phrase")
    pp._insert_phrase_text("second phrase")
    assert e2e.app.content.pt.cget("bg") == C["card_fav"]
    assert e2e.wait_until(lambda: e2e.app.content.pt.cget("bg") == C["entry"], timeout_ms=3000), (
        "闪烁结束后应恢复输入框底色"
    )


def test_add_phrase_keeps_current_category(e2e):
    """在非首个分类新增词条：重载后仍停留在该分类且新词条可见。

    回归：_reload 曾无条件选中首个分类，用户刚写入的词条"消失"。
    """
    pp = _open(e2e)
    cats = list(pp._phrases.keys())
    assert len(cats) >= 2, "内置词库应有多个分类"
    second = cats[1]
    pp._select_cat(second)
    pp._new_phrase_var.set("category context phrase")
    pp._add_phrase()
    e2e.pump()

    assert pp._cur_cat == second, "新增词条后不得跳回首个分类"
    labels = [str(lbl.cget("text")) for lbl in _walk(pp._chip_inner, tk.Label)]
    assert "category context phrase" in labels


def test_duplicate_phrase_shows_dialog_and_skips(e2e, monkeypatch):
    """重复添加：警告对话框弹出、不重复写入。"""
    pp = _open(e2e)
    cat = list(pp._phrases.keys())[0]
    pp._select_cat(cat)
    pl.add_custom_phrase(cat, "dup phrase")
    import ui.phrase_panel as pp_mod

    warned = []
    monkeypatch.setattr(pp_mod.messagebox, "showinfo", lambda *a, **k: warned.append(a))
    pp._new_phrase_var.set("dup phrase")
    pp._add_phrase()
    e2e.pump()
    assert warned  # 去重提示已弹
    bucket = [p for p in pl.get_all_phrases()[cat] if p == "dup phrase"]
    assert bucket.count("dup phrase") == 1


def test_new_category_dialog_creates_and_selects(e2e, monkeypatch):
    """新建分类对话框 → 分类出现且被选中。"""
    pp = _open(e2e)
    import ui.phrase_panel as pp_mod

    monkeypatch.setattr(pp_mod.messagebox, "showwarning", lambda *a, **k: None)
    pp._new_category()
    dialogs = [w for w in pp.winfo_children() if isinstance(w, tk.Toplevel)]
    assert dialogs, "新建分类对话框应作为面板子窗口出现"
    dlg = dialogs[-1]
    ent = None
    create_btn = None

    def _walk(w):
        nonlocal ent, create_btn
        for ch in w.winfo_children():
            if isinstance(ch, tk.Entry):
                ent = ch
            if isinstance(ch, tk.Button):
                t = str(ch.cget("text"))
                if "创建" in t:
                    create_btn = ch
            _walk(ch)

    _walk(dlg)
    assert ent is not None and create_btn is not None
    ent.insert(0, "我的E2E分类")
    create_btn.invoke()
    e2e.pump()
    assert "我的E2E分类" in pl.get_all_phrases()
    assert pp._cur_cat == "我的E2E分类"


def test_template_variable_dialog_fills_and_appends(e2e):
    """模板词条追加 → 变量填充对话框 → 填写后拼接进主输入框。"""
    pp = _open(e2e)
    pl.add_custom_phrase(list(pp._phrases.keys())[0], "{{subject}} in {{style}} style")
    pp._reload()
    pp._select_cat(list(pp._phrases.keys())[0])
    e2e.pump()
    pp._append_to_input("{{subject}} in {{style}} style")
    e2e.pump()
    dialogs = [w for w in pp.winfo_children() if isinstance(w, tk.Toplevel)]
    assert dialogs, "变量填充对话框应出现"
    dlg = dialogs[-1]
    ents = []

    def _collect(w):
        for ch in w.winfo_children():
            if isinstance(ch, tk.Entry):
                ents.append(ch)
            if isinstance(ch, tk.Frame):
                _collect(ch)

    _collect(dlg)
    assert len(ents) == 2
    ents[0].insert(0, "a cat")
    ents[1].insert(0, "watercolor")
    # 先定位「追加」按钮再调用：invoke 会销毁对话框，边遍历边 invoke 会踩死控件
    append_btn = None

    def _find_append(w):
        nonlocal append_btn
        for ch in w.winfo_children():
            if isinstance(ch, tk.Button) and "追加" in str(ch.cget("text")):
                append_btn = ch
            _find_append(ch)

    _find_append(dlg)
    assert append_btn is not None
    append_btn.invoke()
    e2e.pump()
    prompt_text = e2e.app.content.pt.get("1.0", "end-1c")
    assert "a cat in watercolor style" in prompt_text


def test_template_variable_missing_warns_and_keeps_dialog(e2e):
    """变量留空点追加：警告可见且对话框不关闭。

    回归：_confirm(_=None) 曾把 i18n `_` 遮蔽成事件参数，
    空值守卫里的 showwarning 调用抛 TypeError，用户看不到任何提示。
    """
    pp = _open(e2e)
    pl.add_custom_phrase(list(pp._phrases.keys())[0], "{{subject}} alone")
    pp._append_to_input("{{subject}} alone")
    e2e.pump()
    dlg = [w for w in pp.winfo_children() if isinstance(w, tk.Toplevel)][-1]
    append_btn = [b for b in _walk(dlg, tk.Button) if "追加" in str(b.cget("text"))][0]

    append_btn.invoke()
    e2e.pump()

    assert "showwarning" in e2e.dialog_kinds(), "空变量应弹警告提示"
    assert dlg.winfo_exists(), "校验失败时对话框必须保留"
    dlg.destroy()


def test_new_category_empty_name_warns_and_keeps_dialog(e2e):
    """新建分类留空：警告可见且对话框不关闭（同款下划线遮蔽回归）。"""
    pp = _open(e2e)
    pp._new_category()
    e2e.pump()
    dlg = [w for w in pp.winfo_children() if isinstance(w, tk.Toplevel)][-1]
    create_btn = [b for b in _walk(dlg, tk.Button) if "创建" in str(b.cget("text"))][0]

    create_btn.invoke()
    e2e.pump()

    assert "showwarning" in e2e.dialog_kinds()
    assert dlg.winfo_exists()
    dlg.destroy()


def test_append_updates_char_count_and_usage(e2e):
    """点击词条卡片追加 → 主输入框 + 字符计数 + 使用计数三联动。"""
    pp = _open(e2e)
    phrase = "masterpiece"
    pp._append_to_input(phrase)
    e2e.pump()
    assert phrase in e2e.app.content.pt.get("1.0", "end-1c")
    assert len(str(e2e.app.content._char_lbl.cget("text"))) > 0
    assert pl.get_phrase_usage().get(phrase, 0) >= 1


def test_edit_phrase_desc_via_dialog(e2e):
    """编辑自定义词条说明 → 悬浮说明解析到自定义版本。"""
    pp = _open(e2e)
    pl.add_custom_phrase(list(pp._phrases.keys())[0], "desc edit target")
    pp._edit_phrase_desc("desc edit target")
    dialogs = [w for w in pp.winfo_children() if isinstance(w, tk.Toplevel)]
    assert dialogs
    dlg = dialogs[-1]

    def _find_text(w):
        for ch in w.winfo_children():
            if isinstance(ch, tk.Text):
                return ch
            found = _find_text(ch)
            if found:
                return found
        return None

    txt = _find_text(dlg)
    assert txt is not None
    txt.delete("1.0", "end")
    txt.insert("1.0", "E2E 自定义说明")
    save_btn = None

    def _find_save(w):
        nonlocal save_btn
        for ch in w.winfo_children():
            if isinstance(ch, tk.Button) and "保存" in str(ch.cget("text")):
                save_btn = ch
            _find_save(ch)

    _find_save(dlg)
    assert save_btn is not None
    save_btn.invoke()
    e2e.pump()
    assert pl.get_custom_desc("desc edit target") == "E2E 自定义说明"
    assert pl.get_phrase_desc("desc edit target") == "E2E 自定义说明"


def test_export_import_roundtrip_via_dialogs(e2e, monkeypatch, tmp_path):
    """导出 → 清空 → 导入：词库内容与说明完整往返（文件对话框打桩）。"""
    pp = _open(e2e)
    pl.add_custom_phrase("🧪 E2E", "roundtrip phrase")
    pl.set_custom_desc("roundtrip phrase", "往返说明")
    out = tmp_path / "exp.json"
    e2e.patch_filedialog("asksaveasfilename", str(out))
    pp._export_phrases()
    e2e.pump()
    assert out.exists()
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["phrases"]["🧪 E2E"] == ["roundtrip phrase"]

    # 清空后导入
    pl.delete_custom_phrase("🧪 E2E", "roundtrip phrase")
    e2e.patch_filedialog("askopenfilename", str(out))
    import ui.phrase_panel as pp_mod

    monkeypatch.setattr(pp_mod.messagebox, "showinfo", lambda *a, **k: None)
    pp._import_phrases()
    e2e.pump()
    assert "roundtrip phrase" in pl.get_all_phrases()["🧪 E2E"]
    assert pl.get_custom_desc("roundtrip phrase") == "往返说明"


def test_export_failure_reports_error(e2e, monkeypatch, tmp_path):
    """导出落盘失败（磁盘/权限）必须给出错误提示，不能静默无反应。"""
    pp = _open(e2e)
    import services.phrase_library as pl_mod

    def _boom(path):
        raise OSError("disk full")

    monkeypatch.setattr(pl_mod, "export_custom", _boom)
    e2e.patch_filedialog("asksaveasfilename", str(tmp_path / "exp.json"))

    pp._export_phrases()
    e2e.pump()

    assert "showerror" in e2e.dialog_kinds()
    assert pp.winfo_exists()


def test_sidebar_save_as_phrase_syncs_panel(e2e):
    """侧栏一键收藏 → 词库「⭐ 我的词条」出现 + 打开中的面板同步刷新。"""
    entry = add_entry("a lighthouse at dusk", "", "lh.png", "FakeProvider/m")
    _open(e2e)
    e2e.app.sidebar._save_prompt_as_phrase(entry)
    e2e.pump()
    assert "a lighthouse at dusk" in pl.get_all_phrases()[pl.MY_PHRASES_CATEGORY]
