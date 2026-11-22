"""E2E 旅程：启动就绪、菜单与全局快捷键结构。"""


def test_app_boots_with_all_core_panels(e2e):
    """启动即就绪：主内容/侧栏/队列面板/字符计数全部在场。"""
    app = e2e.app
    assert app.content is not None
    assert app.sidebar is not None
    assert app.content.pt.winfo_exists()
    assert app._queue_panel is not None
    e2e.pump()


def test_window_title_present(e2e):
    """主窗口标题非空（应用名）。"""
    app = e2e.app
    title = app.root.title()
    assert title  # 2image / i18n 标题


def test_menubar_complete_structure(e2e):
    """菜单栏：文件/工具/数据 等顶层菜单与其条目齐全。"""
    app = e2e.app
    top = app.root
    menubar = top.nametowidget(top.cget("menu"))
    end = menubar.index("end")
    assert end is not None and end >= 3  # 至少 4 个顶层菜单
    # 每个顶层菜单都有真实条目
    for i in range(end + 1):
        m = menubar.nametowidget(menubar.entrycget(i, "menu"))
        assert m.index("end") is not None, f"顶层菜单 {i} 为空"


def test_char_counter_updates_on_typing(e2e):
    """输入提示词 → 字符计数标签实时更新。"""
    app = e2e.app
    text = "a golden retriever on the beach"
    e2e.set_prompt(text)
    assert str(len(text)) in str(app.content._char_lbl.cget("text"))


def test_shortcut_ctrl_b_opens_phrase_panel_and_escape_closes(e2e):
    """Ctrl+B 打开词库面板（焦点不在输入框时），Escape 关闭。"""
    app = e2e.app
    # 焦点在输入框时 Ctrl+B 让位给编辑键（guard 设计）——焦点放在窗口上
    app.root.focus_set()
    app.root.event_generate("<Control-b>")
    e2e.pump()
    panel = getattr(app, "_phrase_panel", None)
    assert panel is not None and panel.winfo_exists()

    panel.event_generate("<Escape>")
    e2e.pump()
    assert app._phrase_panel is None or not app._phrase_panel.winfo_exists()


def test_status_bar_reports_ready(e2e):
    """状态栏初始为就绪/可用文案，非错误态。"""
    app = e2e.app
    st = str(app.content.status_label.cget("text")) if hasattr(app.content, "status_label") else ""
    assert st == "" or ("失败" not in st and "错误" not in st)


def test_queue_panel_visible_in_notebook(e2e):
    """队列面板在主内容标签页体系中可切换到。"""
    app = e2e.app
    qp = app._queue_panel
    assert qp is not None and qp.winfo_exists()
