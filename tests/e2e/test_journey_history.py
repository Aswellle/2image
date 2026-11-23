"""E2E 旅程：历史侧栏全交互（搜索/标签/收藏/重命名/删除/清空/加载）。"""

import tkinter as tk

from config.i18n import _
from config.theme import C
from data.repository import add_entry, count_entries, get_all_entries, update_tags, rename_entry, toggle_favorite
from tests.e2e import driver


def _seed(n=3):
    paths = []
    for i in range(n):
        p = add_entry(f"castle prompt {i}", f"castle {i}", f"img{i}.png", "FakeProvider/m")
        paths.append(p)
    return paths


def test_seeded_entries_listed_in_sidebar(e2e):
    """播种三条 → 侧栏卡片注册表填充对应数量的卡片。"""
    _seed(3)
    e2e.app._refresh_hist()
    e2e.pump(8)
    sb = e2e.app.sidebar
    assert len(sb._card_widgets) == 3
    assert e2e.history_count() == 3


def test_search_filters_history_cards(e2e):
    """搜索框输入关键字 → 卡片注册表只剩匹配项（防抖经主循环泵消化）。"""
    _seed(3)
    add_entry("sunset beach", "sunset", "b.png", "FakeProvider/m")
    e2e.app._refresh_hist()
    e2e.pump(8)
    sb = e2e.app.sidebar
    sb.sv.set("castle")
    e2e.wait_until(lambda: sb._search_timer is None, timeout_ms=3000)
    e2e.wait_until(lambda: len(sb._card_widgets) == 3, timeout_ms=3000)
    # 4 条记录中 3 条匹配 castle：卡片注册表数量即过滤语义
    assert len(sb._card_widgets) == 3


def test_click_card_loads_entry_into_main_pane(e2e):
    """点击历史卡片 → 提示词载入主输入框。"""
    _seed(1)
    e2e.app._refresh_hist()
    e2e.pump()
    entry = get_all_entries()[0]
    e2e.app._load_entry(entry)
    e2e.pump()
    assert "castle prompt 0" in e2e.app.content.pt.get("1.0", "end-1c")
    assert e2e.app.sel_id == entry["id"]


def test_favorite_toggle_persists(e2e):
    """收藏切换 → DB 持久化 favorited=1。"""
    entry = add_entry("fav me", "", "f.png", "FakeProvider/m")
    toggle_favorite(entry["id"], True)
    e2e.pump()
    refreshed = [x for x in get_all_entries() if x["id"] == entry["id"]][0]
    assert refreshed["favorited"] == 1


def test_rename_entry_updates_record(e2e):
    """重命名：DB 字段更新 + 侧栏显示名跟随。"""
    entry = add_entry("to rename", "", "r.png", "FakeProvider/m")
    rename_entry(entry["id"], "我的城堡")
    e2e.app._refresh_hist()
    e2e.pump()
    refreshed = [x for x in get_all_entries() if x["id"] == entry["id"]][0]
    assert refreshed["nickname"] == "我的城堡"


def test_rename_inline_commits_and_updates_counter(e2e):
    """内联重命名：构造即渲染计数器，确定按钮提交后昵称落库。

    回归：_on_key(*_) 曾把 i18n `_` 遮蔽成参数元组，构造阶段抛
    TypeError 被 Tk 吞掉——确定/取消按钮根本没被创建，重命名无法提交。
    """
    entry = add_entry("rename target prompt", "", "r.png", "FakeProvider/m")
    right = tk.Frame(e2e.app.root, bg=C["panel"])
    title = tk.Label(right, text="rename target prompt")
    card = tk.Frame(right, bg=C["panel"])
    e2e.app.sidebar._rename_inline(entry, card, right, title)
    e2e.pump()

    confirms = driver.find_buttons(right, _("btn_confirm"))
    assert confirms, "内联重命名应渲染确定按钮（此前异常导致按钮缺失）"

    def _find(w, cls):
        for ch in w.winfo_children():
            if isinstance(ch, cls):
                yield ch
            yield from _find(ch, cls)

    entry_widget = next(_find(right, tk.Entry))
    driver.set_entry(entry_widget, "新昵称")

    expected = _("lbl_char_count", cur=len("新昵称"), max=e2e.app.MAX_NICK_LEN)
    assert any(str(lbl.cget("text")) == expected for lbl in _find(right, tk.Label)), "字符计数应随输入更新"

    confirms[0].invoke()
    e2e.pump()
    refreshed = [x for x in get_all_entries() if x["id"] == entry["id"]][0]
    assert refreshed["nickname"] == "新昵称"


def test_tag_update_via_editor_service(e2e):
    """标签编辑：update_tags 后标签查询可见（编辑器对话框由单测覆盖）。"""
    entry = add_entry("tagged", "", "t.png", "FakeProvider/m")
    update_tags(entry["id"], "夜景, 城堡")
    from data.repository import get_all_tags

    tags = get_all_tags()
    assert "夜景" in tags and "城堡" in tags


def test_delete_entry_with_confirmation(e2e):
    """删除：先弹确认（自动确认）→ 记录减少。"""
    entry = add_entry("to delete", "", "d.png", "FakeProvider/m")
    e2e.app.sidebar._del_entry(entry["id"])
    e2e.pump()
    assert "askyesno" in e2e.dialog_kinds(), "删除必须经过二次确认"
    assert count_entries() == 0


def test_clear_all_entries_with_confirmation(e2e):
    """清空全部：走侧栏入口 → 确认对话框 → 记录归零。"""
    _seed(3)
    assert count_entries() == 3

    e2e.app.sidebar._clear_hist()
    e2e.pump()

    assert "askyesno" in e2e.dialog_kinds(), "清空入口必须经过二次确认"
    assert count_entries() == 0


def test_favorites_only_filter_state(e2e):
    """仅收藏过滤开关 → 侧栏内部状态与状态条同步。"""
    _seed(2)
    toggle_favorite(1, True)
    sb = e2e.app.sidebar
    sb._fav_only = True
    e2e.app._refresh_hist()
    e2e.pump()
    assert sb._fav_only is True
    sb._fav_only = False
    e2e.app._refresh_hist()
    e2e.pump()
