"""tests/test_error_experience.py — 错误体验全覆盖护栏。

错误呈现三层（状态栏概述 / 结构化日志 / 弹窗下一步）的数据契约：
  · ProviderError.provider / .next_step 属性
  · _net 统一抛错出口填充 provider
  · format_error_record 单行结构化格式
  · UI _err 的弹窗码表（配置类弹、网络类不弹）
"""

from unittest.mock import patch

import pytest

from services.generation.errors import (
    NEXT_STEP_BY_CODE,
    ProviderAuthError,
    ProviderConfigError,
    ProviderQuotaError,
    ProviderTransientError,
    format_error_record,
)
from services.providers._net import raise_provider_error


class TestNextStepMapping:
    def test_all_codes_have_next_step(self):
        """每个已注册错误码都必须有用户下一步指引。"""
        for code in (
            "not_configured",
            "auth_failed",
            "quota_exhausted",
            "rate_limited",
            "policy_rejected",
            "invalid_request",
            "invalid_response",
            "transient",
            "provider_error",
        ):
            assert NEXT_STEP_BY_CODE.get(code), f"错误码 {code} 缺少下一步指引"

    def test_next_step_property_by_class(self):
        assert "API Key" in ProviderAuthError("bad key").next_step or "Key" in ProviderAuthError("bad").next_step
        assert "充值" in ProviderQuotaError("no balance").next_step or "换" in ProviderQuotaError("x").next_step
        assert "30" in ProviderTransientError("boom").next_step or "网络" in ProviderTransientError("x").next_step
        assert "填写" in ProviderConfigError("need key").next_step


class TestProviderAttribute:
    def test_explicit_provider_kept(self):
        err = ProviderAuthError("bad", provider="gemini")
        assert err.provider == "gemini"

    def test_classify_http_error_carries_provider(self):
        from services.generation.errors import classify_http_error

        err = classify_http_error(429, "Rate limited", provider="siliconflow")
        assert err.provider == "siliconflow"
        assert err.code == "rate_limited"

    def test_raise_provider_error_fills_provider(self):
        with pytest.raises(ProviderAuthError) as ei:
            raise_provider_error("xai_grok", status=401, detail="bad key")
        assert ei.value.provider == "xai_grok"
        assert ei.value.next_step

    def test_raise_provider_error_kind_quota(self):
        with pytest.raises(ProviderQuotaError) as ei:
            raise_provider_error("segmind", kind="quota", detail="insufficient")
        assert ei.value.provider == "segmind"


class TestFormatErrorRecord:
    def test_typed_error_single_line(self):
        err = ProviderAuthError("Key 无效", provider="gemini")
        record = format_error_record(err)
        assert record.startswith("code=auth_failed provider=gemini ")
        assert "detail=Key 无效" in record
        assert "next=" in record
        assert "\n" not in record  # 单行可检索

    def test_unhandled_exception_record(self):
        record = format_error_record(RuntimeError("boom"))
        assert record.startswith("code=unhandled provider=- ")
        assert "RuntimeError: boom" in record

    def test_multiline_detail_flattened(self):
        err = ProviderTransientError("line1\nline2\nline3", provider="gemini")
        assert "\n" not in format_error_record(err)


class TestUiErrDialogGating:
    """弹窗按错误码触发：配置/鉴权/配额弹，网络与限流不弹。"""

    def _make_app(self):
        import tkinter as tk

        import data.repository as repo
        import ui.app as app_mod
        from config.fonts import init_fonts
        from config.settings import DEFAULT_CONFIG

        repo._set_test_db(":memory:")
        repo.init_db()
        init_fonts()
        cfg = dict(DEFAULT_CONFIG)
        cfg["show_wizard_on_start"] = False
        app_mod.load_config = lambda: dict(cfg)
        app_mod.save_config = lambda c: None
        top = tk.Toplevel()
        return app_mod, app_mod.App(top), top

    def test_dialog_codes_set(self):
        # 弹窗码表以常量形式存在于 _err 源码中（AST 免 Tk 依赖）
        import ast
        import pathlib

        src = pathlib.Path("ui/app.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        found = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "dialog_codes" for t in node.targets):
                found = {e.value for e in node.value.elts}
        assert found == {"not_configured", "auth_failed", "quota_exhausted"}

    def test_showwarning_only_for_dialog_codes(self):
        """网络/限流类错误不触发 messagebox，配置类触发一次。"""
        app_mod, app, top = self._make_app()
        try:
            calls = []

            def _run_after(delay, cb, *a):
                cb()  # 立即执行 after 回调，不等事件循环

            with patch("ui.app.messagebox") as mb, patch.object(app.root, "after", side_effect=_run_after):
                mb.showwarning.side_effect = lambda *a, **k: calls.append(a)
                app._err(ProviderAuthError("Key 无效", provider="gemini"))
                assert len(calls) == 1
                # 正文含原始错误与下一步指引
                assert "Key 无效" in calls[0][1]
                app._err(ProviderTransientError("网络错误", provider="gemini"))
                assert len(calls) == 1  # 不弹
                app._err(ProviderConfigError("需要配置 API Key"))
                assert len(calls) == 2
        finally:
            try:
                top.destroy()
            except Exception:
                pass

    def test_structured_log_written(self):
        app_mod, app, top = self._make_app()
        try:
            logs = []
            with patch.object(app, "_log", side_effect=lambda m: logs.append(m)):
                app._err(ProviderAuthError("Key 无效", provider="gemini"))
            joined = "\n".join(logs)
            assert "code=auth_failed" in joined
            assert "provider=gemini" in joined
            assert "next=" in joined
        finally:
            try:
                top.destroy()
            except Exception:
                pass
