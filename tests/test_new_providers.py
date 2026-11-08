"""
tests/test_new_providers.py — 新增模型接口测试

覆盖 volcengine_ark、GPT-Image 2/2.5、Gemini Nano Banana 版本选择
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from config.model_catalog import (
    ARK_IMAGE_DEFAULT,
    ARK_IMAGE_NAMES,
    ARK_IMAGE_MODELS,
    ARK_SEEDREAM_40_T2I,
    ARK_SEEDREAM_45_T2I,
    GPT_IMAGE_2,
    GPT_IMAGE_DEFAULT,
    GPT_IMAGE_NAMES,
    GPT_IMAGE_MODELS,
    GPT_IMAGE_25_FLARE,
    GPT_IMAGE_25_SUNBURST,
    GPT_IMAGE_26_FLARE,
    GPT_IMAGE_26_SUNBURST,
    GEMINI_IMAGE_DEFAULT,
    GEMINI_IMAGE_MODELS,
    GEMINI_NB_21,
    GEMINI_NB_V1,
    GEMINI_NB_V2,
    GEMINI_NB_V2_LITE,
    GEMINI_NB_PRO,
)


# ── 模型目录测试 ─────────────────────────────────────────────────────────────


class TestModelCatalog:
    """验证 model_catalog 常量完整性"""

    def test_gpt_image_models_complete(self):
        """GPT-Image 目录应为 2/2.5/2.6 五个在册型号（旧 1 系已移除）"""
        assert GPT_IMAGE_2 in GPT_IMAGE_MODELS
        assert GPT_IMAGE_25_FLARE in GPT_IMAGE_MODELS
        assert GPT_IMAGE_25_SUNBURST in GPT_IMAGE_MODELS
        assert GPT_IMAGE_26_FLARE in GPT_IMAGE_MODELS
        assert GPT_IMAGE_26_SUNBURST in GPT_IMAGE_MODELS
        assert len(GPT_IMAGE_MODELS) == 5

    def test_gpt_image_retired_models_removed(self):
        """已关停/即将移除的 gpt-image-1 系不得再出现在目录"""
        assert "gpt-image-1" not in GPT_IMAGE_MODELS
        assert "gpt-image-1-mini" not in GPT_IMAGE_MODELS
        assert "gpt-image-1.5" not in GPT_IMAGE_MODELS

    def test_gpt_image_default_is_v2(self):
        """默认模型应为 gpt-image-2"""
        assert GPT_IMAGE_DEFAULT == GPT_IMAGE_2

    def test_gpt_image_names_complete(self):
        """所有 GPT-Image 型号都应有可读名称"""
        for model_id in GPT_IMAGE_MODELS:
            assert model_id in GPT_IMAGE_NAMES, f"{model_id} 缺少可读名称"
            assert len(GPT_IMAGE_NAMES[model_id]) > 0

    def test_gpt_image_26_present(self):
        """2026-11-04 发布的 2.6 系列应在目录中"""
        assert GPT_IMAGE_26_FLARE in GPT_IMAGE_MODELS
        assert GPT_IMAGE_26_SUNBURST in GPT_IMAGE_MODELS

    def test_gemini_models_complete(self):
        """Gemini Nano Banana 系列应包含 5 个型号（含官方推荐的 2.1）"""
        assert GEMINI_NB_21 in GEMINI_IMAGE_MODELS
        assert GEMINI_NB_V1 in GEMINI_IMAGE_MODELS
        assert GEMINI_NB_V2 in GEMINI_IMAGE_MODELS
        assert GEMINI_NB_V2_LITE in GEMINI_IMAGE_MODELS
        assert GEMINI_NB_PRO in GEMINI_IMAGE_MODELS
        assert len(GEMINI_IMAGE_MODELS) == 5

    def test_gemini_default_is_21(self):
        """默认 Gemini 模型应为官方推荐的 Nano Banana 2.1"""
        assert GEMINI_IMAGE_DEFAULT == GEMINI_NB_21

    def test_gemini_deprecated_marked(self):
        """v1 应标记为弃用"""
        from config.model_catalog import GEMINI_IMAGE_DEPRECATED

        assert GEMINI_NB_V1 in GEMINI_IMAGE_DEPRECATED
        assert GEMINI_NB_V2 not in GEMINI_IMAGE_DEPRECATED

    def test_ark_models_complete(self):
        """豆包系列应包含 4 个型号，4.0 用正式快照 ID"""
        from config.model_catalog import ARK_SEEDREAM_30_T2I, ARK_SEEDIT_30_I2I

        assert ARK_SEEDREAM_45_T2I in ARK_IMAGE_MODELS
        assert ARK_SEEDREAM_40_T2I == "doubao-seedream-4-0-250828"
        assert ARK_SEEDREAM_30_T2I in ARK_IMAGE_MODELS
        assert ARK_SEEDIT_30_I2I in ARK_IMAGE_MODELS
        assert len(ARK_IMAGE_MODELS) == 4

    def test_ark_default_is_seedream_45(self):
        """默认豆包模型应为 Seedream 4.5"""
        assert ARK_IMAGE_DEFAULT == ARK_SEEDREAM_45_T2I

    def test_ark_names_readable(self):
        """所有豆包型号都应有可读名称"""
        for model_id in ARK_IMAGE_MODELS:
            assert model_id in ARK_IMAGE_NAMES, f"{model_id} 缺少可读名称"


# ── volcengine_ark Provider 测试 ────────────────────────────────────────────


class TestVolcengineArkProvider:
    """测试火山引擎豆包 provider"""

    def test_provider_info(self):
        from services.providers.volcengine_ark import PROVIDER_INFO

        assert PROVIDER_INFO["id"] == "volcengine_ark"
        assert PROVIDER_INFO["config_key"] == "volcengine_key"
        assert PROVIDER_INFO["category"] == "commercial"

    def test_missing_key_raises_valueerror(self):
        from services.providers.volcengine_ark import try_volcengine_ark

        with pytest.raises(ValueError, match="火山引擎"):
            try_volcengine_ark("test", 64, 64, 42, {}, print)

    def test_missing_key_empty_raises_valueerror(self):
        from services.providers.volcengine_ark import try_volcengine_ark

        with pytest.raises(ValueError, match="火山引擎"):
            try_volcengine_ark("test", 64, 64, 42, {"volcengine_key": "  "}, print)

    @patch("services.providers.volcengine_ark._get_session")
    @patch("services.providers.volcengine_ark._safe_get_image")
    def test_text2image_success(self, mock_safe_get, mock_session):
        from services.providers.volcengine_ark import try_volcengine_ark

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}
        mock_session.return_value.post.return_value = mock_resp

        # 图片下载走 safe_get_image 安全通道（SSRF 校验），直接 mock 其返回
        mock_safe_get.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        cfg = {"volcengine_key": "test-key", "ark_model": ARK_SEEDREAM_40_T2I}
        data, name = try_volcengine_ark("a cat", 64, 64, 42, cfg, print)

        assert data == b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert "豆包" in name
        assert "Seedream 4.0" in name

    @patch("services.providers.volcengine_ark._get_session")
    @patch("services.providers.volcengine_ark._safe_get_image")
    def test_invalid_model_normalized(self, mock_safe_get, mock_session):
        """存量无效模型值（旧的 -t2i 后缀 ID）应归一化到目录默认"""
        from services.providers.volcengine_ark import try_volcengine_ark

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}
        mock_session.return_value.post.return_value = mock_resp
        mock_safe_get.return_value = b"\x89PNG" + b"\x00" * 50

        cfg = {"volcengine_key": "test-key", "ark_model": "doubao-seedream-4-0-t2i"}
        _, name = try_volcengine_ark("a cat", 64, 64, 42, cfg, print)
        assert "Seedream 4.5" in name  # 归一化到 4.5 默认

        sent_model = mock_session.return_value.post.call_args[1]["json"]["model"]
        assert sent_model == ARK_IMAGE_DEFAULT

    @patch("services.providers.volcengine_ark._get_session")
    def test_text2image_b64_response(self, mock_session):
        from services.providers.volcengine_ark import try_volcengine_ark

        img_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100).decode()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"b64_json": img_b64}]}
        mock_session.return_value.post.return_value = mock_resp

        cfg = {"volcengine_key": "test-key"}
        data, name = try_volcengine_ark("a cat", 64, 64, 42, cfg, print)

        assert data == b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    @patch("services.providers.volcengine_ark._get_session")
    def test_401_raises_auth_error(self, mock_session):
        from services.providers.volcengine_ark import try_volcengine_ark

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_session.return_value.post.return_value = mock_resp

        cfg = {"volcengine_key": "bad-key"}
        with pytest.raises((ValueError, RuntimeError), match="无效或已过期"):
            try_volcengine_ark("a cat", 64, 64, 42, cfg, print)

    @patch("services.providers.volcengine_ark._get_session")
    def test_empty_data_raises_error(self, mock_session):
        from services.providers.volcengine_ark import try_volcengine_ark

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}
        mock_session.return_value.post.return_value = mock_resp

        cfg = {"volcengine_key": "test-key"}
        with pytest.raises((ValueError, RuntimeError), match="无图片"):
            try_volcengine_ark("a cat", 64, 64, 42, cfg, print)


# ── OpenAI GPT-Image 2.5 测试 ───────────────────────────────────────────────


class TestOpenAIGPTImage25:
    """测试 OpenAI GPT-Image 2.5 型号支持"""

    @patch("services.providers.openai_image._get_session")
    def test_gpt_image_25_26_any_size(self, mock_session):
        """GPT-Image 2.5 / 2.6 型号请求应带任意尺寸（gpt-image-2+ 家族）"""
        from services.providers.openai_image import _gpt2_size, try_openai_image

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"b64_json": base64.b64encode(b"img").decode()}]}
        mock_session.return_value.post.return_value = mock_resp

        for model in [GPT_IMAGE_25_FLARE, GPT_IMAGE_25_SUNBURST, GPT_IMAGE_26_FLARE, GPT_IMAGE_26_SUNBURST]:
            cfg = {"openai_key": "test-key", "gpt_image_model": model}
            try_openai_image("a cat", 512, 512, 42, cfg, lambda m: None)
            body = mock_session.return_value.post.call_args.kwargs.get("json") or {}
            assert body.get("model") == model
            assert body.get("size") == _gpt2_size(512, 512)

    @patch("services.providers.openai_image._get_session")
    def test_stale_gpt_image_1_normalized(self, mock_session):
        """存量 gpt-image-1 系配置值应归一化到默认（旧 ID 已关停/移除）"""
        from services.providers.openai_image import try_openai_image
        from config.model_catalog import GPT_IMAGE_DEFAULT

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"b64_json": base64.b64encode(b"img").decode()}]}
        mock_session.return_value.post.return_value = mock_resp

        for stale in ("gpt-image-1", "gpt-image-1-mini", "gpt-image-1.5"):
            cfg = {"openai_key": "test-key", "gpt_image_model": stale}
            try_openai_image("a cat", 512, 512, 42, cfg, lambda m: None)
            body = mock_session.return_value.post.call_args.kwargs.get("json") or {}
            assert body.get("model") == GPT_IMAGE_DEFAULT


# ── Gemini Nano Banana 版本选择测试 ────────────────────────────────────────


class TestGeminiNanoBanana:
    """测试 Gemini Nano Banana 版本选择"""

    @patch("services.providers.gemini._get_session")
    def test_default_model_is_21(self, mock_session):
        """默认应使用官方推荐的 Nano Banana 2.1"""
        from services.providers.gemini import try_gemini

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"inlineData": {"data": base64.b64encode(b"img").decode()}}]}}]
        }
        mock_session.return_value.post.return_value = mock_resp

        cfg = {"gemini_key": "test-key"}
        try_gemini("a cat", 64, 64, 42, cfg, lambda m: None)

        call_args = mock_session.return_value.post.call_args
        url = call_args[0][0]
        assert "gemini-nano-banana-2.1" in url

    @patch("services.providers.gemini._get_session")
    def test_v1_model_selection(self, mock_session):
        """应支持选择 v1 legacy 模型（官方存活至 2027-03）"""
        from services.providers.gemini import try_gemini

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"inlineData": {"data": base64.b64encode(b"img").decode()}}]}}]
        }
        mock_session.return_value.post.return_value = mock_resp

        cfg = {"gemini_key": "test-key", "gemini_model": "gemini-2.5-flash-image"}
        try_gemini("a cat", 64, 64, 42, cfg, lambda m: None)

        call_args = mock_session.return_value.post.call_args
        url = call_args[0][0]
        assert "gemini-2.5-flash-image" in url

    @patch("services.providers.gemini._get_session")
    def test_pro_model_selection(self, mock_session):
        """应支持选择 Pro 模型"""
        from services.providers.gemini import try_gemini

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"inlineData": {"data": base64.b64encode(b"img").decode()}}]}}]
        }
        mock_session.return_value.post.return_value = mock_resp

        cfg = {"gemini_key": "test-key", "gemini_model": "gemini-3-pro-image"}
        try_gemini("a cat", 64, 64, 42, cfg, lambda m: None)

        call_args = mock_session.return_value.post.call_args
        url = call_args[0][0]
        assert "gemini-3-pro-image" in url


# ── Provider 注册表测试 ─────────────────────────────────────────────────────


class TestProviderRegistry:
    """验证新 provider 正确注册"""

    def test_volcengine_in_all_providers(self):
        from services.providers import ALL_PROVIDERS, COMMERCIAL_PROVIDERS

        assert "volcengine_ark" in ALL_PROVIDERS
        assert "volcengine_ark" in COMMERCIAL_PROVIDERS

    def test_openai_image_in_paid_providers(self):
        from services.providers import PAID_PROVIDERS

        assert "openai_image" in PAID_PROVIDERS

    def test_gemini_in_free_providers(self):
        from services.providers import FREE_PROVIDERS

        assert "gemini" in FREE_PROVIDERS
