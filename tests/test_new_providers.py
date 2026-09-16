"""
tests/test_new_providers.py — 新增模型接口测试

覆盖 volcengine_ark、GPT-Image 2/2.5、Gemini Nano Banana 版本选择
"""
from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from config.model_catalog import (
    ARK_IMAGE_DEFAULT, ARK_IMAGE_NAMES, ARK_IMAGE_MODELS,
    GPT_IMAGE_1, GPT_IMAGE_1_MINI, GPT_IMAGE_1_5, GPT_IMAGE_2,
    GPT_IMAGE_DEFAULT, GPT_IMAGE_NAMES, GPT_IMAGE_MODELS,
    GPT_IMAGE_25_FLARE, GPT_IMAGE_25_SUNBURST,
    GEMINI_IMAGE_DEFAULT, GEMINI_IMAGE_NAMES, GEMINI_IMAGE_MODELS,
    GEMINI_NB_V1, GEMINI_NB_V2, GEMINI_NB_V2_LITE, GEMINI_NB_PRO,
)


# ── 模型目录测试 ─────────────────────────────────────────────────────────────


class TestModelCatalog:
    """验证 model_catalog 常量完整性"""

    def test_gpt_image_models_complete(self):
        """GPT-Image 系列应包含所有 6 个型号"""
        assert GPT_IMAGE_1 in GPT_IMAGE_MODELS
        assert GPT_IMAGE_1_MINI in GPT_IMAGE_MODELS
        assert GPT_IMAGE_1_5 in GPT_IMAGE_MODELS
        assert GPT_IMAGE_2 in GPT_IMAGE_MODELS
        assert GPT_IMAGE_25_FLARE in GPT_IMAGE_MODELS
        assert GPT_IMAGE_25_SUNBURST in GPT_IMAGE_MODELS
        assert len(GPT_IMAGE_MODELS) == 6

    def test_gpt_image_default_is_v2(self):
        """默认模型应为 gpt-image-2"""
        assert GPT_IMAGE_DEFAULT == GPT_IMAGE_2

    def test_gpt_image_names_complete(self):
        """所有 GPT-Image 型号都应有可读名称"""
        for model_id in GPT_IMAGE_MODELS:
            assert model_id in GPT_IMAGE_NAMES, f"{model_id} 缺少可读名称"
            assert len(GPT_IMAGE_NAMES[model_id]) > 0

    def test_gpt_image_legacy_marked(self):
        """旧版模型应标记为 Legacy"""
        from config.model_catalog import GPT_IMAGE_LEGACY
        assert GPT_IMAGE_1 in GPT_IMAGE_LEGACY
        assert GPT_IMAGE_2 not in GPT_IMAGE_LEGACY

    def test_gemini_models_complete(self):
        """Gemini Nano Banana 系列应包含 4 个型号"""
        assert GEMINI_NB_V1 in GEMINI_IMAGE_MODELS
        assert GEMINI_NB_V2 in GEMINI_IMAGE_MODELS
        assert GEMINI_NB_V2_LITE in GEMINI_IMAGE_MODELS
        assert GEMINI_NB_PRO in GEMINI_IMAGE_MODELS
        assert len(GEMINI_IMAGE_MODELS) == 4

    def test_gemini_default_is_v2(self):
        """默认 Gemini 模型应为 Nano Banana 2"""
        assert GEMINI_IMAGE_DEFAULT == GEMINI_NB_V2

    def test_gemini_deprecated_marked(self):
        """v1 应标记为弃用"""
        from config.model_catalog import GEMINI_IMAGE_DEPRECATED
        assert GEMINI_NB_V1 in GEMINI_IMAGE_DEPRECATED
        assert GEMINI_NB_V2 not in GEMINI_IMAGE_DEPRECATED

    def test_ark_models_complete(self):
        """豆包系列应包含 3 个型号"""
        from config.model_catalog import ARK_SEEDREAM_30_T2I, ARK_SEEDREAM_40_T2I, ARK_SEEDIT_30_I2I
        assert ARK_SEEDREAM_30_T2I in ARK_IMAGE_MODELS
        assert ARK_SEEDREAM_40_T2I in ARK_IMAGE_MODELS
        assert ARK_SEEDIT_30_I2I in ARK_IMAGE_MODELS
        assert len(ARK_IMAGE_MODELS) == 3

    def test_ark_default_is_seedream_40(self):
        """默认豆包模型应为 Seedream 4.0"""
        assert ARK_IMAGE_DEFAULT == "doubao-seedream-4-0-t2i"

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

    @patch("services.providers.volcengine_ark._session")
    def test_text2image_success(self, mock_session):
        from services.providers.volcengine_ark import try_volcengine_ark

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"url": "https://example.com/img.png"}]
        }
        mock_session.post.return_value = mock_resp

        mock_img_resp = MagicMock()
        mock_img_resp.status_code = 200
        mock_img_resp.content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mock_img_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_img_resp

        cfg = {"volcengine_key": "test-key", "ark_model": "doubao-seedream-4-0-t2i"}
        data, name = try_volcengine_ark("a cat", 64, 64, 42, cfg, print)

        assert data == b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert "豆包" in name
        assert "Seedream 4.0" in name

    @patch("services.providers.volcengine_ark._session")
    def test_text2image_b64_response(self, mock_session):
        from services.providers.volcengine_ark import try_volcengine_ark

        img_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100).decode()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"b64_json": img_b64}]
        }
        mock_session.post.return_value = mock_resp

        cfg = {"volcengine_key": "test-key"}
        data, name = try_volcengine_ark("a cat", 64, 64, 42, cfg, print)

        assert data == b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    @patch("services.providers.volcengine_ark._session")
    def test_401_raises_auth_error(self, mock_session):
        from services.providers.volcengine_ark import try_volcengine_ark

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_session.post.return_value = mock_resp

        cfg = {"volcengine_key": "bad-key"}
        with pytest.raises((ValueError, RuntimeError), match="无效或已过期"):
            try_volcengine_ark("a cat", 64, 64, 42, cfg, print)

    @patch("services.providers.volcengine_ark._session")
    def test_empty_data_raises_error(self, mock_session):
        from services.providers.volcengine_ark import try_volcengine_ark

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}
        mock_session.post.return_value = mock_resp

        cfg = {"volcengine_key": "test-key"}
        with pytest.raises((ValueError, RuntimeError), match="无图片"):
            try_volcengine_ark("a cat", 64, 64, 42, cfg, print)


# ── OpenAI GPT-Image 2.5 测试 ───────────────────────────────────────────────


class TestOpenAIGPTImage25:
    """测试 OpenAI GPT-Image 2.5 型号支持"""

    def test_gpt_image_25_in_size_routing(self):
        """GPT-Image 2.5 型号应走 gpt-image-2+ 尺寸路由"""
        from services.providers.openai_image import _size_for, _gpt2_size

        for model in [GPT_IMAGE_25_FLARE, GPT_IMAGE_25_SUNBURST]:
            size = _size_for(model, 512, 512)
            assert size == _gpt2_size(512, 512)

    def test_gpt_image_1_uses_preset(self):
        """GPT-Image 1 家族应使用预设尺寸"""
        from services.providers.openai_image import _size_for

        for model in ["gpt-image-1", "gpt-image-1-mini", "gpt-image-1.5"]:
            size = _size_for(model, 512, 512)
            assert size == "1024x1024"


# ── Gemini Nano Banana 版本选择测试 ────────────────────────────────────────


class TestGeminiNanoBanana:
    """测试 Gemini Nano Banana 版本选择"""

    @patch("services.providers.gemini._session")
    def test_default_model_is_v2(self, mock_session):
        """默认应使用 Nano Banana 2"""
        from services.providers.gemini import try_gemini

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [
                        {"inlineData": {"data": base64.b64encode(b"img").decode()}}
                    ]
                }
            }]
        }
        mock_session.post.return_value = mock_resp

        cfg = {"gemini_key": "test-key"}
        try_gemini("a cat", 64, 64, 42, cfg, lambda m: None)

        call_args = mock_session.post.call_args
        url = call_args[0][0]
        assert "gemini-3.1-flash-image" in url

    @patch("services.providers.gemini._session")
    def test_v1_model_selection(self, mock_session):
        """应支持选择 v1 模型"""
        from services.providers.gemini import try_gemini

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [
                        {"inlineData": {"data": base64.b64encode(b"img").decode()}}
                    ]
                }
            }]
        }
        mock_session.post.return_value = mock_resp

        cfg = {"gemini_key": "test-key", "gemini_model": "gemini-2.5-flash-image"}
        try_gemini("a cat", 64, 64, 42, cfg, lambda m: None)

        call_args = mock_session.post.call_args
        url = call_args[0][0]
        assert "gemini-2.5-flash-image" in url

    @patch("services.providers.gemini._session")
    def test_pro_model_selection(self, mock_session):
        """应支持选择 Pro 模型"""
        from services.providers.gemini import try_gemini

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [
                        {"inlineData": {"data": base64.b64encode(b"img").decode()}}
                    ]
                }
            }]
        }
        mock_session.post.return_value = mock_resp

        cfg = {"gemini_key": "test-key", "gemini_model": "gemini-3-pro-image"}
        try_gemini("a cat", 64, 64, 42, cfg, lambda m: None)

        call_args = mock_session.post.call_args
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
