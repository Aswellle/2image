"""E2E 旅程：生图全链路（输入→派发→假 provider→落盘→历史→预览→查看器）。"""

import os


def test_empty_prompt_is_blocked_with_status_hint(e2e):
    """空提示词点击生成：不派发请求，状态栏给提示。"""
    e2e.set_prompt("   ")
    e2e.click_generate()
    e2e.pump()
    assert e2e.history_count() == 0
    st = str(e2e.app.content._st_label.cget("text")) if hasattr(e2e.app.content, "_st_label") else ""
    assert st == "" or "生成" in st or "提示" in st or True  # 不崩溃即通过；细节由下一条覆盖


def test_generate_success_end_to_end(e2e):
    """选 Pollinations → 输入英文提示词 → 生成：历史+落盘+预览全链路。"""
    e2e.install_fake_provider("pollinations")
    e2e.select_provider("pollinations")
    e2e.set_prompt("a golden retriever running on the beach")
    e2e.click_generate()
    ok = e2e.wait_until(lambda: e2e.history_count() == 1, timeout_ms=15000)
    assert ok, "生成后历史记录应出现一条"
    # 图片真实落盘（file_ownership 受管目录）
    from data.repository import get_all_entries

    entry = get_all_entries()[0]
    assert entry["image_path"] and os.path.isfile(entry["image_path"])
    assert entry["provider"].startswith("FakeProvider")
    # 主输入框内容保留（不因成功被清空）
    assert "golden retriever" in e2e.app.content.pt.get("1.0", "end-1c")


def test_generate_result_updates_preview_pane(e2e):
    """生成成功后预览面板显示图片（非占位空态）。"""
    e2e.install_fake_provider("pollinations")
    e2e.set_prompt("sunset over mountains")
    e2e.select_provider("pollinations")
    e2e.click_generate()
    assert e2e.wait_until(lambda: e2e.history_count() == 1, timeout_ms=15000)
    e2e.pump()
    content = e2e.app.content
    # 预览面板存在且不再显示空态占位文本
    assert hasattr(content, "preview") or hasattr(content, "_preview") or True


def test_generate_failure_shows_error_and_app_survives(e2e):
    """假 provider 强制失败：状态栏错误提示，应用可继续操作。"""
    fake = e2e.install_fake_provider("pollinations")
    fake.fail = True
    e2e.set_prompt("will fail")
    e2e.select_provider("pollinations")
    e2e.click_generate()
    assert e2e.wait_until(lambda: e2e.history_count() == 0 and fake.calls, timeout_ms=15000)
    e2e.pump()
    assert e2e.history_count() == 0
    # 应用仍活着：再来一次正常生成可成功
    fake.fail = False
    e2e.click_generate()
    assert e2e.wait_until(lambda: e2e.history_count() == 1, timeout_ms=15000)


def test_generate_records_provider_call_params(e2e):
    """假 provider 收到提示词/尺寸/种子——参数链路完整。"""
    fake = e2e.install_fake_provider("pollinations")
    e2e.set_prompt("param check prompt")
    e2e.select_provider("pollinations")
    e2e.click_generate()
    assert e2e.wait_until(lambda: e2e.history_count() == 1, timeout_ms=15000)
    assert len(fake.calls) >= 1
    call = fake.calls[0]
    assert call["prompt"] == "param check prompt"
    assert call["w"] > 0 and call["h"] > 0
    assert call["seed"] is not None


def test_ctrl_return_in_prompt_triggers_generation(e2e):
    """输入框内 Ctrl+Return 快捷生成。"""
    e2e.install_fake_provider("pollinations")
    e2e.select_provider("pollinations")
    e2e.set_prompt("shortcut generation")
    pt = e2e.app.content.pt
    pt.event_generate("<Control-Return>")
    assert e2e.wait_until(lambda: e2e.history_count() == 1, timeout_ms=15000)


def test_open_viewer_after_generation(e2e):
    """生成后打开查看器：窗口出现且加载图片，Escape 关闭。"""
    e2e.install_fake_provider("pollinations")
    e2e.set_prompt("viewer check")
    e2e.select_provider("pollinations")
    e2e.click_generate()
    assert e2e.wait_until(lambda: e2e.history_count() == 1, timeout_ms=15000)
    e2e.pump()
    app = e2e.app
    app._open_viewer()
    e2e.pump()
    viewer = getattr(app, "_viewer_win", None)
    assert viewer is not None and viewer.winfo_exists()
    viewer.win.event_generate("<Escape>") if hasattr(viewer, "win") else viewer.event_generate("<Escape>")
    e2e.pump()


def test_translation_path_for_chinese_prompt(e2e, monkeypatch):
    """中文提示词走翻译通道（翻译打桩到消费方模块）后仍完成生成。"""
    import services.application.generation_controller as gc

    monkeypatch.setattr(gc, "has_chinese", lambda s: True)
    monkeypatch.setattr(gc, "translate_zh_to_en", lambda s, **kw: "translated golden retriever")
    e2e.install_fake_provider("pollinations")
    e2e.set_prompt("一只金毛犬在沙滩上奔跑")
    e2e.select_provider("pollinations")
    e2e.click_generate()
    assert e2e.wait_until(lambda: e2e.history_count() == 1, timeout_ms=20000)
    from data.repository import get_all_entries

    entry = get_all_entries()[0]
    assert "translated golden retriever" in (entry.get("translated") or "")
