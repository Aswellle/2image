"""
tests/test_provider_contract2.py — Provider 契约测试 harness（第二批）
─────────────────────────────────────────────────────────────────────
覆盖剩余低覆盖率 provider：fal_flux / stablehorde / huggingface /
modelslab / segmind / xai_grok。全部 mock HTTP，绝不打公网 API。
"""

import base64
from unittest.mock import MagicMock, patch

import pytest

from services.generation.errors import ProviderQuotaError

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-image-data" * 100  # ≥1024B，满足 provider 的最小尺寸校验
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")


def _resp(status=200, json_data=None, content=b"", content_type="application/json", headers=None):
    m = MagicMock()
    m.status_code = status
    m.headers = headers if headers is not None else {"Content-Type": content_type}
    if json_data is not None:
        m.json.return_value = json_data
    else:
        m.json.side_effect = ValueError("no json")
    m.content = content
    # 支持流式读取（read_bounded 走 iter_content）
    m.iter_content.return_value = iter([content]) if content else iter([])
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
        with (
            patch(f"{self.MOD}._get_session", return_value=sess),
            patch.object(mod.time, "sleep"),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            data, used = mod.try_fal_flux("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "FLUX.2-Pro" in used
        assert "fal-ai/flux-2-pro" in sess.post.call_args.args[0]
        body = sess.post.call_args.kwargs["json"]
        assert body["image_size"] == {"width": 1024, "height": 1024}

    def test_i2i_uses_img2img_queue(self):
        import services.providers.fal_flux as mod

        sess = MagicMock()
        sess.post.return_value = _resp(200, {"request_id": "rid1234567890"})
        sess.get.side_effect = [
            _resp(200, {"status": "COMPLETED"}),
            _resp(200, {"images": [{"url": "https://cdn.example.com/f.png"}]}),
        ]
        cfg = {**self.CFG, "_ref_image": PNG_BYTES}
        with (
            patch(f"{self.MOD}._get_session", return_value=sess),
            patch.object(mod.time, "sleep"),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            mod.try_fal_flux("cat", 1024, 1024, 1, cfg, lambda s: None)
        assert "fal-ai/flux-2-pro/edit" in sess.post.call_args.args[0]
        body = sess.post.call_args.kwargs["json"]
        assert body["image_urls"] and body["image_urls"][0].startswith("data:image/png;base64,")

    def test_401(self):
        import services.providers.fal_flux as mod

        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=_resp(401)))):
            with pytest.raises(ValueError, match="Key 无效"):
                mod.try_fal_flux("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_429(self):
        import services.providers.fal_flux as mod

        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=_resp(429)))):
            with pytest.raises(ValueError, match="速率限制"):
                mod.try_fal_flux("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_poll_failed_status(self):
        import services.providers.fal_flux as mod

        sess = MagicMock()
        sess.post.return_value = _resp(200, {"request_id": "rid1234567890"})
        sess.get.return_value = _resp(200, {"status": "FAILED"})
        with patch(f"{self.MOD}._get_session", return_value=sess), patch.object(mod.time, "sleep"):
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
            _resp(200, {"done": True, "wait_time": 0}),  # check
            _resp(
                200,
                {
                    "generations": [  # status
                        {"img": "https://r2.example.com/a.png", "model": "DreamShaper XL"}
                    ]
                },
            ),
        ]
        with (
            patch(f"{self.MOD}._get_session", return_value=sess),
            patch.object(mod.time, "sleep"),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            data, used = mod.try_stablehorde("cat", 512, 512, 1, {}, lambda s: None)  # 空 key = 匿名
        assert data == PNG_BYTES and "StableHorde" in used

    def test_401_rejected(self):
        import services.providers.stablehorde as mod

        sess = MagicMock(post=MagicMock(return_value=_resp(401)))
        with patch(f"{self.MOD}._get_session", return_value=sess):
            with pytest.raises(ValueError, match="Key 无效"):
                mod.try_stablehorde("cat", 512, 512, 1, {"stablehorde_key": "bad"}, lambda s: None)

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
        with patch(f"{self.MOD}._get_session", return_value=sess), patch.object(mod.time, "sleep"):
            with pytest.raises(ValueError, match="faulted"):
                mod.try_stablehorde("cat", 512, 512, 1, {}, lambda s: None)

    def test_submit_exhausted(self):
        import services.providers.stablehorde as mod

        sess = MagicMock(post=MagicMock(return_value=_resp(429, headers={})))
        with patch(f"{self.MOD}._get_session", return_value=sess), patch.object(mod.time, "sleep"):
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
        with patch(f"{self.MOD}._get_session", return_value=sess), patch.object(mod.time, "sleep"):
            with pytest.raises(ValueError, match="generations"):
                mod.try_stablehorde("cat", 512, 512, 1, {}, lambda s: None)


# ── HuggingFace（多模型回退 + 多响应格式）──────────────────────


class TestHuggingFace:
    MOD = "services.providers.huggingface"
    CFG = {"hf_token": "hf-test"}

    def test_success_direct_image(self):
        import services.providers.huggingface as mod

        resp = _resp(200, content=PNG_BYTES, content_type="image/png")
        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, used = mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "HuggingFace" in used

    def test_success_list_b64(self):
        import services.providers.huggingface as mod

        resp = _resp(200, json_data=[{"generated_image": PNG_B64}])
        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, _ = mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_success_data_b64(self):
        import services.providers.huggingface as mod

        resp = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, _ = mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_success_images_url(self):
        import services.providers.huggingface as mod

        resp = _resp(200, json_data={"images": [{"url": "https://cdn.example.com/h.png"}]})
        with (
            patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            data, _ = mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401(self):
        import services.providers.huggingface as mod

        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=_resp(401)))):
            with pytest.raises(ValueError, match="Token 无效"):
                mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_429_then_success(self):
        import services.providers.huggingface as mod

        ok = _resp(200, content=PNG_BYTES, content_type="image/png")
        sess = MagicMock()
        sess.post.side_effect = [_resp(429, headers={}), ok]
        with patch(f"{self.MOD}._get_session", return_value=sess), patch.object(mod.time, "sleep"):
            data, _ = mod.try_hf_inference("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_all_models_fail(self):
        import services.providers.huggingface as mod

        with (
            patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=_resp(500)))),
            patch.object(mod.time, "sleep"),
        ):
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

        resp = _resp(200, json_data={"status": "success", "output": ["https://cdn.example.com/m.png"]})
        with (
            patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            data, used = mod.try_modelslab("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "ModelsLab" in used

    def test_success_via_poll(self):
        import services.providers.modelslab as mod

        sess = MagicMock()
        sess.post.side_effect = [
            _resp(200, json_data={"status": "processing", "id": "req1"}),
            _resp(200, json_data={"status": "success", "output": ["https://cdn.example.com/m.png"]}),
        ]
        with (
            patch(f"{self.MOD}._get_session", return_value=sess),
            patch.object(mod.time, "sleep"),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            data, _ = mod.try_modelslab("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401(self):
        import services.providers.modelslab as mod

        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=_resp(401)))):
            with pytest.raises(ValueError, match="Key 无效"):
                mod.try_modelslab("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_402_quota(self):
        import services.providers.modelslab as mod

        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=_resp(402)))):
            with pytest.raises(ValueError, match="额度"):
                mod.try_modelslab("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_all_models_fail(self):
        import services.providers.modelslab as mod

        resp = _resp(200, json_data={"status": "error", "message": "x"})
        with (
            patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))),
            patch.object(mod.time, "sleep"),
        ):
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
        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, used = mod.try_segmind("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "Segmind" in used

    def test_success_direct_image(self):
        import services.providers.segmind as mod

        resp = _resp(200, content=PNG_BYTES, content_type="image/png")
        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, _ = mod.try_segmind("cat", 512, 512, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401(self):
        import services.providers.segmind as mod

        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=_resp(401)))):
            with pytest.raises(ValueError, match="Key 无效"):
                mod.try_segmind("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_402_quota(self):
        import services.providers.segmind as mod

        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=_resp(402)))):
            with pytest.raises(ValueError, match="额度不足"):
                mod.try_segmind("cat", 512, 512, 1, self.CFG, lambda s: None)

    def test_429_then_success(self):
        import services.providers.segmind as mod

        ok = _resp(200, json_data={"image": PNG_B64})
        sess = MagicMock()
        sess.post.side_effect = [_resp(429, headers={}), ok]
        with patch(f"{self.MOD}._get_session", return_value=sess), patch.object(mod.time, "sleep"):
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
        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, used = mod.try_xai_grok("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "xAI" in used

    def test_success_url(self):
        import services.providers.xai_grok as mod

        resp = _resp(200, json_data={"data": [{"url": "https://cdn.example.com/x.jpg"}]})
        with (
            patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            data, _ = mod.try_xai_grok("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_401_auth_error_not_retried(self):
        """401 → ProviderAuthError 立即抛出（不再重试后 RuntimeError）。"""
        import services.providers.xai_grok as mod
        from services.generation.errors import ProviderAuthError

        with (
            patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=_resp(401)))),
            patch.object(mod.time, "sleep"),
        ):
            with pytest.raises(ProviderAuthError):
                mod.try_xai_grok("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_429_then_success(self):
        import services.providers.xai_grok as mod

        ok = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        sess = MagicMock()
        sess.post.side_effect = [_resp(429), ok]
        with patch(f"{self.MOD}._get_session", return_value=sess), patch.object(mod.time, "sleep"):
            data, _ = mod.try_xai_grok("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_missing_key(self):
        import services.providers.xai_grok as mod

        with pytest.raises(ValueError, match="Key"):
            mod.try_xai_grok("cat", 1024, 1024, 1, {}, lambda s: None)

    # ── 请求体钉子（2026-11 官方生图指南参数）──────────────────

    def test_payload_model_aspect_resolution(self):
        """默认模型/宽高比取最接近枚举/分辨率按长边分档。"""
        import services.providers.xai_grok as mod
        from config.model_catalog import XAI_IMAGE_DEFAULT

        ok = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        sess = MagicMock(post=MagicMock(return_value=ok))
        with patch(f"{self.MOD}._get_session", return_value=sess):
            mod.try_xai_grok("cat", 1344, 768, 7, self.CFG, lambda s: None)
        body = sess.post.call_args.kwargs["json"]
        assert body["model"] == XAI_IMAGE_DEFAULT
        assert body["aspect_ratio"] == "16:9"  # 1.75 最贴近 16/9
        assert body["resolution"] == "2k"  # 长边 1344 > 1024
        assert body["n"] == 1 and body["prompt"] == "cat"

        sess2 = MagicMock(post=MagicMock(return_value=ok))
        with patch(f"{self.MOD}._get_session", return_value=sess2):
            mod.try_xai_grok("cat", 1024, 1024, 7, self.CFG, lambda s: None)
        body2 = sess2.post.call_args.kwargs["json"]
        assert body2["aspect_ratio"] == "1:1" and body2["resolution"] == "1k"

    def test_configured_model_honored_when_unknown(self):
        """无 UI 族策略：目录外手改值按原样请求（自救助手），不静默改写。"""
        import services.providers.xai_grok as mod

        ok = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        sess = MagicMock(post=MagicMock(return_value=ok))
        cfg = {**self.CFG, "xai_model": "grok-imagine-image"}
        with patch(f"{self.MOD}._get_session", return_value=sess):
            _, used = mod.try_xai_grok("cat", 1024, 1024, 1, cfg, lambda s: None)
        assert sess.post.call_args.kwargs["json"]["model"] == "grok-imagine-image"
        assert "grok-imagine-image" in used

        cfg_new = {**self.CFG, "xai_model": "grok-imagine-image-3.0"}
        sess2 = MagicMock(post=MagicMock(return_value=ok))
        with patch(f"{self.MOD}._get_session", return_value=sess2):
            mod.try_xai_grok("cat", 1024, 1024, 1, cfg_new, lambda s: None)
        # 未在册的新快照 ID 原样送出（warn-but-honor）
        assert sess2.post.call_args.kwargs["json"]["model"] == "grok-imagine-image-3.0"


# ── Together AI ────────────────────────────────────────────────


class TestTogetherAi:
    MOD = "services.providers.together_ai"
    CFG = {"together_key": "tk-test"}

    def test_success_b64(self):
        import services.providers.together_ai as mod

        resp = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        with patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))):
            data, used = mod.try_together_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES and "TogetherAI" in used

    def test_success_url(self):
        import services.providers.together_ai as mod

        resp = _resp(200, json_data={"data": [{"url": "https://cdn.example.com/t.png"}]})
        with (
            patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=resp))),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            data, _ = mod.try_together_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_402_quota_retries_then_runtime(self):
        import services.providers.together_ai as mod

        with (
            patch(f"{self.MOD}._get_session", return_value=MagicMock(post=MagicMock(return_value=_resp(402)))),
            patch.object(mod.time, "sleep"),
        ):
            with pytest.raises(ProviderQuotaError):
                mod.try_together_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)

    def test_429_then_success(self):
        import services.providers.together_ai as mod

        ok = _resp(200, json_data={"data": [{"b64_json": PNG_B64}]})
        sess = MagicMock()
        sess.post.side_effect = [_resp(429), ok]
        with patch(f"{self.MOD}._get_session", return_value=sess), patch.object(mod.time, "sleep"):
            data, _ = mod.try_together_ai("cat", 1024, 1024, 1, self.CFG, lambda s: None)
        assert data == PNG_BYTES

    def test_missing_key(self):
        import services.providers.together_ai as mod

        with pytest.raises(ValueError, match="Together"):
            mod.try_together_ai("cat", 1024, 1024, 1, {}, lambda s: None)


# ── Replicate FLUX（按官方 schema 分家构造请求）────────────────


class TestReplicateFlux:
    MOD = "services.providers.replicate_flux"
    CFG = {"replicate_key": "rk-test"}

    def _mock(self):
        ok = _resp(200, json_data={"id": "pred123", "status": "succeeded", "output": ["https://cdn.example.com/f.png"]})
        return MagicMock(post=MagicMock(return_value=ok))

    def test_flux2_pro_payload_shape(self):
        import services.providers.replicate_flux as mod

        sess = self._mock()
        with (
            patch(f"{self.MOD}._get_session", return_value=sess),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            _, used = mod.try_replicate("cat", 1024, 1024, 5, self.CFG, lambda s: None)
        inp = sess.post.call_args.kwargs["json"]["input"]
        assert inp["prompt"] == "cat"
        assert inp["aspect_ratio"] == "custom"
        assert inp["width"] % 16 == 0 and inp["height"] % 16 == 0
        assert 256 <= inp["width"] <= 2048 and 256 <= inp["height"] <= 2048
        assert inp["output_format"] == "png"
        assert "num_outputs" not in inp  # 官方 schema 无此字段
        assert "black-forest-labs/flux-2-pro" in sess.post.call_args.args[0]
        assert "flux-2-pro" in used

    def test_flux_11_pro_clamps_32(self):
        import services.providers.replicate_flux as mod

        sess = self._mock()
        cfg = {**self.CFG, "replicate_model": "flux-1.1-pro"}
        with (
            patch(f"{self.MOD}._get_session", return_value=sess),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            mod.try_replicate("cat", 1000, 1000, 5, cfg, lambda s: None)
        inp = sess.post.call_args.kwargs["json"]["input"]
        assert inp["width"] % 32 == 0 and inp["height"] % 32 == 0
        assert 256 <= inp["width"] <= 1440

    def test_flux_dev_steps_guidance(self):
        import services.providers.replicate_flux as mod

        sess = self._mock()
        cfg = {**self.CFG, "replicate_model": "flux-dev"}
        with (
            patch(f"{self.MOD}._get_session", return_value=sess),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            mod.try_replicate("cat", 1024, 1024, 5, cfg, lambda s: None)
        inp = sess.post.call_args.kwargs["json"]["input"]
        assert inp["num_inference_steps"] == 28 and inp["guidance_scale"] == 3.5

    def test_stale_slug_normalized(self):
        """旧下拉里的无效项（flux-schnell 等）归一化到默认并记日志。"""
        import services.providers.replicate_flux as mod

        sess = self._mock()
        cfg = {**self.CFG, "replicate_model": "flux-schnell"}
        with (
            patch(f"{self.MOD}._get_session", return_value=sess),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            mod.try_replicate("cat", 1024, 1024, 5, cfg, lambda s: None)
        assert "black-forest-labs/flux-2-pro" in sess.post.call_args.args[0]


# ── BFL FLUX（FLUX.2 单端点生成+编辑）──────────────────────────


class TestBflFlux:
    MOD = "services.providers.bfl_flux"
    CFG = {"bfl_key": "bk-test"}

    def _ok(self):
        return _resp(200, json_data={"id": "t1", "polling_url": "https://api.bfl.ai/v1/get_result?id=t1"})

    def _poll_ready(self):
        return _resp(200, json_data={"status": "Ready", "result": {"sample": "https://cdn.example.com/b.png"}})

    def _run(self, cfg):
        import services.providers.bfl_flux as mod

        sess = MagicMock()
        sess.post.return_value = self._ok()
        sess.get.return_value = self._poll_ready()
        with (
            patch(f"{self.MOD}._get_session", return_value=sess),
            patch(f"{self.MOD}._safe_get_image", return_value=PNG_BYTES),
        ):
            out = mod.try_bfl_flux("cat", 1024, 1024, 9, cfg, lambda s: None)
        return sess, out

    def test_default_model_and_payload(self):
        sess, (data, used) = self._run(self.CFG)
        assert data == PNG_BYTES and "flux-2-pro" in used
        assert sess.post.call_args.args[0].endswith("/v1/flux-2-pro")
        body = sess.post.call_args.kwargs["json"]
        assert body["prompt"] == "cat" and body["width"] % 32 == 0
        assert body["output_format"] == "png"
        assert "input_image" not in body

    def test_i2i_forces_flux2_pro_for_unverified_models(self):
        """编辑输入仅对 2-pro 验证：1.1-pro / 2-max 配置下图生图一律走 2-pro。"""
        for model in ("flux-pro-1.1", "flux-2-max"):
            sess, _ = self._run({**self.CFG, "bfl_model": model, "_ref_image": PNG_BYTES})
            assert sess.post.call_args.args[0].endswith("/v1/flux-2-pro"), model
            assert "input_image" in sess.post.call_args.kwargs["json"]

    def test_i2i_keeps_configured_2pro(self):
        sess, _ = self._run({**self.CFG, "bfl_model": "flux-2-pro", "_ref_image": PNG_BYTES})
        assert sess.post.call_args.args[0].endswith("/v1/flux-2-pro")
        body = sess.post.call_args.kwargs["json"]
        assert body["input_image"]  # base64 参考图
