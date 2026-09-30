"""
tests/test_provider_contract.py — Provider 通用契约测试 harness
────────────────────────────────────────────────────────────────
覆盖覆盖率最低的 6 个 provider 的关键路径（TEST-001）：

  · 成功路径（b64 / URL 下载 / 轮询）
  · 401 认证失败（不得静默成功）
  · 429 限流（退避后重试成功）
  · 5xx / 业务错误 → ValueError/RuntimeError

全部通过 patch 模块级 `_get_session` / `_safe_get_image` / time.sleep 实现，
绝不打公网 API（tests/fakes 同一原则）。
"""
import base64
from unittest.mock import MagicMock, patch

import pytest

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-image-data" * 16
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")


def _resp(status=200, json_data=None, content=b"", content_type="application/json"):
    """构造一个 requests.Response 形状的 mock。"""
    m = MagicMock()
    m.status_code = status
    m.headers = {"Content-Type": content_type}
    if json_data is not None:
        m.json.return_value = json_data
    else:
        m.json.side_effect = ValueError("no json")
    m.content = content
    m.raise_for_status.return_value = None
    return m


def _fake_session(post=None, get=None):
    sess = MagicMock()
    if post is not None:
        sess.post.return_value = post
    if get is not None:
        sess.get.return_value = get
    return sess


# ── 火山引擎豆包 ───────────────────────────────────────────────

class TestVolcengineArk:
    MOD = "services.providers.volcengine_ark"
    CFG = {"volcengine_key": "vk-test"}

    def test_success_b64(self):
        import services.providers.volcengine_ark as mod
        sess = _fake_session(post=_resp(200, {"data": [{"b64_json": PNG_B64}]}))
        with patch(f"{self.MOD}._get_session", return_value=sess):
            data, used = mod.try_volcengine_ark("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "豆包" in used

    def test_success_url_download(self):
        import services.providers.volcengine_ark as mod
        sess = _fake_session(
            post=_resp(200, {"data": [{"url": "https://cdn.example.com/x.png"}]}),
            get=_resp(200, content=PNG_BYTES),
        )
        with patch(f"{self.MOD}._get_session", return_value=sess):
            data, _ = mod.try_volcengine_ark("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401_retries_then_runtime_error(self):
        import services.providers.volcengine_ark as mod
        sess = _fake_session(post=_resp(401, json_data=None))
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(RuntimeError, match="全部重试失败"):
                mod.try_volcengine_ark("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert sess.post.call_count == 3  # _MAX_RETRIES

    def test_429_backoff_then_success(self):
        import services.providers.volcengine_ark as mod
        ok = _resp(200, {"data": [{"b64_json": PNG_B64}]})
        sess = _fake_session(post=_resp(429, json_data=None))
        sess.post.side_effect = [_resp(429, json_data=None), ok]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            data, _ = mod.try_volcengine_ark("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_empty_items_raises(self):
        import services.providers.volcengine_ark as mod
        sess = _fake_session(post=_resp(200, {"data": []}))
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(RuntimeError, match="全部重试失败"):
                mod.try_volcengine_ark("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_missing_key(self):
        import services.providers.volcengine_ark as mod
        with pytest.raises(ValueError, match="Key"):
            mod.try_volcengine_ark("cat", 1024, 1024, 1, {}, lambda s: None)


# ── Stability AI（无内部重试，错误直接抛出）─────────────────────

class TestStabilityAi:
    MOD = "services.providers.stability_ai"
    CFG = {"stability_key": "sk-test"}

    def test_success_json_b64(self):
        import services.providers.stability_ai as mod
        resp = _resp(200, {"artifacts": [{"base64": PNG_B64}]})
        with patch(f"{self.MOD}._get_session", return_value=_fake_session(post=resp)):
            data, used = mod.try_stability_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "StabilityAI" in used

    def test_success_direct_image(self):
        import services.providers.stability_ai as mod
        resp = _resp(200, content=PNG_BYTES, content_type="image/png")
        with patch(f"{self.MOD}._get_session", return_value=_fake_session(post=resp)):
            data, _ = mod.try_stability_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401(self):
        import services.providers.stability_ai as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=_fake_session(post=_resp(401))):
            with pytest.raises(ValueError, match="Key"):
                mod.try_stability_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_402_balance(self):
        import services.providers.stability_ai as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=_fake_session(post=_resp(402))):
            with pytest.raises(ValueError, match="余额"):
                mod.try_stability_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_422_params(self):
        import services.providers.stability_ai as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=_fake_session(post=_resp(422, {"errors": ["bad"]}))):
            with pytest.raises(ValueError, match="参数错误"):
                mod.try_stability_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_500(self):
        import services.providers.stability_ai as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=_fake_session(post=_resp(500))):
            with pytest.raises(ValueError, match="500"):
                mod.try_stability_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_img2img_mode(self):
        import services.providers.stability_ai as mod
        resp = _resp(200, {"artifacts": [{"base64": PNG_B64}]})
        sess = _fake_session(post=resp)
        cfg = {**self.CFG, "_ref_image": PNG_BYTES, "_ref_strength": 0.5}
        with patch(f"{self.MOD}._get_session", return_value=sess):
            data, used = mod.try_stability_ai("cat", 1024, 1024, 1, cfg, lambda s: None)
        assert data == PNG_BYTES and "img2img" in used


# ── Replicate FLUX（提交 + 轮询）───────────────────────────────

class TestReplicate:
    MOD = "services.providers.replicate_flux"
    CFG = {"replicate_key": "rk-test"}

    def test_success_data_uri(self):
        import services.providers.replicate_flux as mod
        out = [f"data:image/png;base64,{PNG_B64}"]
        resp = _resp(200, {"id": "p1", "status": "succeeded", "output": out})
        with patch(f"{self.MOD}._get_session", return_value=_fake_session(post=resp)):
            data, used = mod.try_replicate("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "Replicate" in used

    def test_poll_success(self):
        import services.providers.replicate_flux as mod
        submit = _resp(200, {"id": "pred12345678", "status": "starting"})
        poll = _resp(200, {"id": "pred12345678", "status": "succeeded",
                           "output": [f"data:image/png;base64,{PNG_B64}"]})
        sess = _fake_session(post=submit, get=poll)
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            data, _ = mod.try_replicate("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401(self):
        import services.providers.replicate_flux as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=_fake_session(post=_resp(401))):
            with pytest.raises(ValueError, match="Token"):
                mod.try_replicate("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_failed_status(self):
        import services.providers.replicate_flux as mod
        submit = _resp(200, {"id": "pred12345678", "status": "starting"})
        poll = _resp(200, {"status": "failed", "error": "NSFW"})
        sess = _fake_session(post=submit, get=poll)
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(ValueError, match="任务失败"):
                mod.try_replicate("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_missing_key(self):
        import services.providers.replicate_flux as mod
        with pytest.raises(ValueError, match="Token"):
            mod.try_replicate("cat", 1024, 1024, 1, {}, lambda s: None)


# ── DashScope 通义万相（异步任务）──────────────────────────────

class TestDashscope:
    MOD = "services.providers.dashscope_qwen"
    CFG = {"dashscope_key": "sk-ali-test"}

    def test_success_flow(self):
        import services.providers.dashscope_qwen as mod
        submit = _resp(200, {"output": {"task_id": "task-1"}})
        poll = _resp(200, {"output": {"task_status": "SUCCEEDED",
                                      "results": [{"url": "https://cdn.example.com/a.png"}]}})
        sess = _fake_session(post=submit, get=poll)
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"), \
             patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES):
            data, used = mod.try_dashscope_qwen("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "DashScope" in used

    def test_401(self):
        import services.providers.dashscope_qwen as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=_fake_session(post=_resp(401))):
            with pytest.raises(ValueError, match="Key 无效"):
                mod.try_dashscope_qwen("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_submit_500(self):
        import services.providers.dashscope_qwen as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=_fake_session(post=_resp(500))):
            with pytest.raises(ValueError, match="提交失败"):
                mod.try_dashscope_qwen("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_task_failed(self):
        import services.providers.dashscope_qwen as mod
        submit = _resp(200, {"output": {"task_id": "task-1"}})
        poll = _resp(200, {"output": {"task_status": "FAILED", "message": "content policy"}})
        sess = _fake_session(post=submit, get=poll)
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(ValueError, match="任务失败"):
                mod.try_dashscope_qwen("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_missing_key(self):
        import services.providers.dashscope_qwen as mod
        with pytest.raises(ValueError, match="DashScope"):
            mod.try_dashscope_qwen("cat", 1024, 1024, 1, {}, lambda s: None)


# ── MiniMax ────────────────────────────────────────────────────

class TestMiniMax:
    MOD = "services.providers.minimax_image"
    CFG = {"minimax_key": "mm-test"}

    def test_success_b64(self):
        import services.providers.minimax_image as mod
        resp = _resp(200, {"data": {"image_base64": [PNG_B64]},
                           "base_resp": {"status_code": 0}})
        with patch(f"{self.MOD}._get_session", return_value=_fake_session(post=resp)):
            data, used = mod.try_minimax_image("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "MiniMax" in used

    def test_429_then_success(self):
        import services.providers.minimax_image as mod
        ok = _resp(200, {"data": {"image_base64": [PNG_B64]},
                         "base_resp": {"status_code": 0}})
        sess = MagicMock()
        sess.post.side_effect = [_resp(429), ok]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            data, _ = mod.try_minimax_image("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_business_error_retries_then_runtime(self):
        import services.providers.minimax_image as mod
        resp = _resp(200, {"base_resp": {"status_code": 1004, "status_msg": "invalid"}})
        with patch(f"{self.MOD}._get_session", return_value=_fake_session(post=resp)), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(RuntimeError, match="全部重试失败"):
                mod.try_minimax_image("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_missing_key(self):
        import services.providers.minimax_image as mod
        with pytest.raises(ValueError, match="Key"):
            mod.try_minimax_image("cat", 1024, 1024, 1, {}, lambda s: None)


# ── Gemini Nano Banana Pro ─────────────────────────────────────

class TestNanoBananaPro:
    MOD = "services.providers.gemini_nano_banana_pro"
    CFG = {"gemini_key": "gk-test"}

    def _ok_resp(self):
        payload = {"candidates": [{"content": {"parts": [
            {"text": "here you go"},
            {"inlineData": {"mimeType": "image/png", "data": PNG_B64}},
        ]}}]}
        return _resp(200, payload)

    def test_success(self):
        import services.providers.gemini_nano_banana_pro as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=_fake_session(post=self._ok_resp())):
            data, used = mod.try_gemini_nano_banana_pro(
                "cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "Nano-Banana-Pro" in used

    def test_429_then_success(self):
        import services.providers.gemini_nano_banana_pro as mod
        sess = MagicMock()
        sess.post.side_effect = [_resp(429), self._ok_resp()]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            data, _ = mod.try_gemini_nano_banana_pro(
                "cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_http_error_retries_then_runtime(self):
        import services.providers.gemini_nano_banana_pro as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=_fake_session(post=_resp(500))), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(RuntimeError, match="全部重试失败"):
                mod.try_gemini_nano_banana_pro(
                    "cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_no_candidates(self):
        import services.providers.gemini_nano_banana_pro as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=_fake_session(post=_resp(200, {"candidates": []}))), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(RuntimeError, match="全部重试失败"):
                mod.try_gemini_nano_banana_pro(
                    "cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_img2img_inline_data(self):
        import services.providers.gemini_nano_banana_pro as mod
        sess = _fake_session(post=self._ok_resp())
        cfg = {**self.CFG, "_ref_image": PNG_BYTES}
        with patch(f"{self.MOD}._get_session", return_value=sess):
            data, _ = mod.try_gemini_nano_banana_pro(
                "cat", 1024, 1024, 1, cfg, lambda s: None)
        assert data == PNG_BYTES
        sent = sess.post.call_args.kwargs["json"]
        assert sent["contents"][0]["parts"][1]["inline_data"]["data"] == PNG_B64

    def test_missing_key(self):
        import services.providers.gemini_nano_banana_pro as mod
        with pytest.raises(ValueError, match="Gemini"):
            mod.try_gemini_nano_banana_pro("cat", 1024, 1024, 1, {}, lambda s: None)
