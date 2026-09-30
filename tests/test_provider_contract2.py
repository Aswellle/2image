"""
tests/test_provider_contract2.py — Provider 契约测试 harness（第二批）
─────────────────────────────────────────────────────────────────────
覆盖剩余低覆盖率 provider：fal_flux / stablehorde / huggingface /
modelslab / segmind / xai_grok。全部 mock HTTP，绝不打公网 API。
"""
import base64
from unittest.mock import MagicMock, patch

import pytest

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-image-data" * 100  # ≥1024B，满足 provider 的最小尺寸校验
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")


def _resp(status=200, json_data=None, content=b"", content_type="application/json",
          headers=None):
    m = MagicMock()
    m.status_code = status
    m.headers = headers if headers is not None else {"Content-Type": content_type}
    if json_data is not None:
        m.json.return_value = json_data
    else:
        m.json.side_effect = ValueError("no json")
    m.content = content
    m.raise_for_status.return_value = None
    return m


# ── fal.ai FLUX（队列提交 + 轮询）──────────────────────────────

class TestFalFlux:
    MOD = "services.providers.fal_flux"
    CFG = {"fal_key": "fk-test"}

    def test_success_t2i(self):
        import services.providers.fal_flux as mod
        sess = MagicMock()
        sess.post.return_value = _resp(200, {"request_id": "rid1234567890"})
        sess.get.side_effect = [
            _resp(200, {"status": "COMPLETED"}),
            _resp(200, {"images": [{"url": "https://cdn.example.com/f.png"}]}),
        ]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"), \
             patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES):
            data, used = mod.try_fal_flux("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "FLUX-Ultra" in used

    def test_i2i_uses_img2img_queue(self):
        import services.providers.fal_flux as mod
        sess = MagicMock()
        sess.post.return_value = _resp(200, {"request_id": "rid1234567890"})
        sess.get.side_effect = [
            _resp(200, {"status": "COMPLETED"}),
            _resp(200, {"images": [{"url": "https://cdn.example.com/f.png"}]}),
        ]
        cfg = {**self.CFG, "_ref_image": PNG_BYTES}
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"), \
             patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES):
            mod.try_fal_flux("cat", 1024, 1024, 1, cfg, lambda s: None)
        assert "image-to-image" in sess.post.call_args.args[0]

    def test_401(self):
        import services.providers.fal_flux as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=_resp(401)))):
            with pytest.raises(ValueError, match="Key 无效"):
                mod.try_fal_flux("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_429(self):
        import services.providers.fal_flux as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=_resp(429)))):
            with pytest.raises(ValueError, match="速率限制"):
                mod.try_fal_flux("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_poll_failed_status(self):
        import services.providers.fal_flux as mod
        sess = MagicMock()
        sess.post.return_value = _resp(200, {"request_id": "rid1234567890"})
        sess.get.return_value = _resp(200, {"status": "FAILED"})
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(ValueError, match="任务失败"):
                mod.try_fal_flux("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_missing_key(self):
        import services.providers.fal_flux as mod
        with pytest.raises(ValueError, match="fal.ai"):
            mod.try_fal_flux("cat", 1024, 1024, 1, {}, lambda s: None)


# ── StableHorde（匿名提交 + 轮询 + R2 下载）────────────────────

class TestStableHorde:
    MOD = "services.providers.stablehorde"

    def test_success_anonymous(self):
        import services.providers.stablehorde as mod
        sess = MagicMock()
        sess.post.return_value = _resp(200, {"id": "job1234567890abcdef"})
        sess.get.side_effect = [
            _resp(200, {"done": True, "wait_time": 0}),       # check
            _resp(200, {"generations": [                      # status
                {"img": "https://r2.example.com/a.png", "model": "DreamShaper XL"}]}),
        ]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"), \
             patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES):
            data, used = mod.try_stablehorde(
                "cat", 512, 512, 1, {}, lambda s: None)   # 空 key = 匿名
        assert data == PNG_BYTES and "StableHorde" in used

    def test_401_rejected(self):
        import services.providers.stablehorde as mod
        sess = MagicMock(post=MagicMock(return_value=_resp(401)))
        with patch(f"{self.MOD}._get_session", return_value=sess):
            with pytest.raises(ValueError, match="Key 无效"):
                mod.try_stablehorde("cat", 512, 512, 1,
                                    {"stablehorde_key": "bad"}, lambda s: None)

    def test_403_rejected(self):
        import services.providers.stablehorde as mod
        sess = MagicMock(post=MagicMock(return_value=_resp(403)))
        with patch(f"{self.MOD}._get_session", return_value=sess):
            with pytest.raises(ValueError, match="403"):
                mod.try_stablehorde("cat", 512, 512, 1, {}, lambda s: None)

    def test_faulted_task(self):
        import services.providers.stablehorde as mod
        sess = MagicMock()
        sess.post.return_value = _resp(200, {"id": "job1234567890abcdef"})
        sess.get.return_value = _resp(200, {"faulted": True})
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(ValueError, match="faulted"):
                mod.try_stablehorde("cat", 512, 512, 1, {}, lambda s: None)

    def test_submit_exhausted(self):
        import services.providers.stablehorde as mod
        sess = MagicMock(post=MagicMock(return_value=_resp(429, headers={})))
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(ValueError, match="提交失败"):
                mod.try_stablehorde("cat", 512, 512, 1, {}, lambda s: None)

    def test_no_generations(self):
        import services.providers.stablehorde as mod
        sess = MagicMock()
        sess.post.return_value = _resp(200, {"id": "job1234567890abcdef"})
        sess.get.side_effect = [
            _resp(200, {"done": True}),
            _resp(200, {"generations": []}),
        ]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(ValueError, match="generations"):
                mod.try_stablehorde("cat", 512, 512, 1, {}, lambda s: None)


# ── HuggingFace（多模型回退 + 多响应格式）──────────────────────

class TestHuggingFace:
    MOD = "services.providers.huggingface"
    CFG = {"hf_token": "hf-test"}

    def test_success_direct_image(self):
        import services.providers.huggingface as mod
        resp = _resp(200, content=PNG_BYTES, content_type="image/png")
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, used = mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "HuggingFace" in used

    def test_success_list_b64(self):
        import services.providers.huggingface as mod
        resp = _resp(200, json_data=[{"generated_image": PNG_B64}])
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, _ = mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_success_data_b64(self):
        import services.providers.huggingface as mod
        resp = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, _ = mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_success_images_url(self):
        import services.providers.huggingface as mod
        resp = _resp(200, json_data={"images": [{"url": "https://cdn.example.com/h.png"}]})
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))), \
             patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES):
            data, _ = mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401(self):
        import services.providers.huggingface as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=_resp(401)))):
            with pytest.raises(ValueError, match="Token 无效"):
                mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_429_then_success(self):
        import services.providers.huggingface as mod
        ok = _resp(200, content=PNG_BYTES, content_type="image/png")
        sess = MagicMock()
        sess.post.side_effect = [_resp(429, headers={}), ok]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            data, _ = mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_all_models_fail(self):
        import services.providers.huggingface as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=_resp(500)))),\
             patch.object(mod.time, "sleep"):
            with pytest.raises(ValueError, match="所有 HuggingFace 模型均失败"):
                mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_missing_key(self):
        import services.providers.huggingface as mod
        with pytest.raises(ValueError, match="Token"):
            mod.try_hf_inference("cat", 512, 512, 1, {}, lambda s: None)


# ── ModelsLab（提交/轮询 + 多模型回退）─────────────────────────

class TestModelsLab:
    MOD = "services.providers.modelslab"
    CFG = {"modelslab_key": "ml-test"}

    def test_success_direct(self):
        import services.providers.modelslab as mod
        resp = _resp(200, json_data={"status": "success",
                                     "output": ["https://cdn.example.com/m.png"]})
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))), \
             patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES):
            data, used = mod.try_modelslab("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "ModelsLab" in used

    def test_success_via_poll(self):
        import services.providers.modelslab as mod
        sess = MagicMock()
        sess.post.side_effect = [
            _resp(200, json_data={"status": "processing", "id": "req1"}),
            _resp(200, json_data={"status": "success",
                                  "output": ["https://cdn.example.com/m.png"]}),
        ]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"), \
             patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES):
            data, _ = mod.try_modelslab("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401(self):
        import services.providers.modelslab as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=_resp(401)))):
            with pytest.raises(ValueError, match="Key 无效"):
                mod.try_modelslab("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_402_quota(self):
        import services.providers.modelslab as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=_resp(402)))):
            with pytest.raises(ValueError, match="额度"):
                mod.try_modelslab("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_all_models_fail(self):
        import services.providers.modelslab as mod
        resp = _resp(200, json_data={"status": "error", "message": "x"})
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(ValueError, match="所有模型均失败"):
                mod.try_modelslab("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_missing_key(self):
        import services.providers.modelslab as mod
        with pytest.raises(ValueError, match="Key"):
            mod.try_modelslab("cat", 512, 512, 1, {}, lambda s: None)


# ── Segmind ────────────────────────────────────────────────────

class TestSegmind:
    MOD = "services.providers.segmind"
    CFG = {"segmind_key": "sg-test"}

    def test_success_b64(self):
        import services.providers.segmind as mod
        resp = _resp(200, json_data={"image": PNG_B64})
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, used = mod.try_segmind("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "Segmind" in used

    def test_success_direct_image(self):
        import services.providers.segmind as mod
        resp = _resp(200, content=PNG_BYTES, content_type="image/png")
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, _ = mod.try_segmind("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401(self):
        import services.providers.segmind as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=_resp(401)))):
            with pytest.raises(ValueError, match="Key 无效"):
                mod.try_segmind("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_402_quota(self):
        import services.providers.segmind as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=_resp(402)))):
            with pytest.raises(ValueError, match="额度不足"):
                mod.try_segmind("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_429_then_success(self):
        import services.providers.segmind as mod
        ok = _resp(200, json_data={"image": PNG_B64})
        sess = MagicMock()
        sess.post.side_effect = [_resp(429, headers={}), ok]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            data, _ = mod.try_segmind("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_missing_key(self):
        import services.providers.segmind as mod
        with pytest.raises(ValueError, match="Segmind"):
            mod.try_segmind("cat", 512, 512, 1, {}, lambda s: None)


# ── xAI Grok ───────────────────────────────────────────────────

class TestXaiGrok:
    MOD = "services.providers.xai_grok"
    CFG = {"xai_key": "xk-test"}

    def test_success_b64(self):
        import services.providers.xai_grok as mod
        resp = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, used = mod.try_xai_grok("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "xAI" in used

    def test_success_url(self):
        import services.providers.xai_grok as mod
        resp = _resp(200, json_data={"data": [{"url": "https://cdn.example.com/x.jpg"}]})
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))), \
             patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES):
            data, _ = mod.try_xai_grok("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401_retries_then_runtime(self):
        import services.providers.xai_grok as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=_resp(401)))), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(RuntimeError, match="全部重试失败"):
                mod.try_xai_grok("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_429_then_success(self):
        import services.providers.xai_grok as mod
        ok = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        sess = MagicMock()
        sess.post.side_effect = [_resp(429), ok]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            data, _ = mod.try_xai_grok("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_missing_key(self):
        import services.providers.xai_grok as mod
        with pytest.raises(ValueError, match="Key"):
            mod.try_xai_grok("cat", 1024, 1024, 1, {}, lambda s: None)


# ── Together AI ────────────────────────────────────────────────

class TestTogetherAi:
    MOD = "services.providers.together_ai"
    CFG = {"together_key": "tk-test"}

    def test_success_b64(self):
        import services.providers.together_ai as mod
        resp = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, used = mod.try_together_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "TogetherAI" in used

    def test_success_url(self):
        import services.providers.together_ai as mod
        resp = _resp(200, json_data={"data": [{"url": "https://cdn.example.com/t.png"}]})
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=resp))), \
             patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES):
            data, _ = mod.try_together_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_402_quota_retries_then_runtime(self):
        import services.providers.together_ai as mod
        with patch(f"{self.MOD}._get_session",
                   return_value=MagicMock(post=MagicMock(return_value=_resp(402)))), \
             patch.object(mod.time, "sleep"):
            with pytest.raises(RuntimeError, match="全部重试失败"):
                mod.try_together_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_429_then_success(self):
        import services.providers.together_ai as mod
        ok = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        sess = MagicMock()
        sess.post.side_effect = [_resp(429), ok]
        with patch(f"{self.MOD}._get_session", return_value=sess), \
             patch.object(mod.time, "sleep"):
            data, _ = mod.try_together_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_missing_key(self):
        import services.providers.together_ai as mod
        with pytest.raises(ValueError, match="Together"):
            mod.try_together_ai("cat", 1024, 1024, 1, {}, lambda s: None)
