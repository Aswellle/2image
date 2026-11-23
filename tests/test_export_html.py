"""tests/test_export_html.py — 历史记录本 HTML 转义回归。"""

from config.i18n import _


def test_export_html_escapes_image_filename(app, monkeypatch, tmp_path):
    """图片文件名进入 src 属性前转义：旧版导入的怪文件名不得注入标记。"""
    a, _saved = app
    import ui.app as app_mod

    monkeypatch.setattr(app_mod.messagebox, "showinfo", lambda *args, **kwargs: None)
    entry = {
        "id": 1,
        "timestamp": "2026-01-01 00:00:00",
        "prompt": "p",
        "translated": "",
        "image_path": '/tmp/a"onload="alert(1).png',
        "provider": "P",
        "nickname": "",
        "favorited": 0,
        "tags": "",
    }
    a._finish_export(str(tmp_path), [entry])

    html_text = (tmp_path / _("export_html_filename")).read_text(encoding="utf-8")
    assert "&quot;" in html_text
    assert 'onload="alert(1)' not in html_text
