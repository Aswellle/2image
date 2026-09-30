"""
tests/test_translation.py — 翻译服务契约（PERF-001）
────────────────────────────────────────────────────
覆盖：缓存命中不出网、成功/失败路径、超长截断、限流等待可取消。
全部 mock HTTP，绝不打真实翻译 API。
"""
import time
from unittest.mock import MagicMock, patch

import pytest

from services.translation import (
    _LAST_DONE,
    _MIN_INTERVAL,
    TranslationCache,
    get_translation_cache,
    has_chinese,
    translate_zh_to_en,
)
from services.generation.cancellation import CancellationToken
from services.generation.errors import GenerationCancelled


def _release_rate_limit():
    """让限流窗口已过，避免测试内等待。"""
    _LAST_DONE[0] = time.time() - (_MIN_INTERVAL + 10)


def _mock_ok(translated: str = "a cute cat"):
    resp = MagicMock()
    resp.json.return_value = {"responseData": {"translatedText": translated}}
    return resp


def test_has_chinese():
    assert has_chinese("月亮上的猫")
    assert not has_chinese("a cat on the moon")
    assert not has_chinese("")


def test_cache_hit_skips_network():
    cache = get_translation_cache()
    text = f"缓存命中测试{time.time_ns()}"
    cache.put(text, "cached-result")
    with patch("services.translation.requests.get") as mock_get:
        result = translate_zh_to_en(text)
    assert result == "cached-result"
    mock_get.assert_not_called()


def test_success_translates_and_caches():
    _release_rate_limit()
    text = f"一只猫{time.time_ns()}"
    with patch("services.translation.requests.get", return_value=_mock_ok("a cat")):
        result = translate_zh_to_en(text)
    assert result == "a cat"
    # 第二次调用走缓存（不出网）
    with patch("services.translation.requests.get") as mock_get:
        assert translate_zh_to_en(text) == "a cat"
        mock_get.assert_not_called()


def test_network_failure_returns_original():
    _release_rate_limit()
    text = f"网络失败原文{time.time_ns()}"
    with patch("services.translation.requests.get",
               side_effect=ConnectionError("down")):
        result = translate_zh_to_en(text)
    assert result == text  # 失败降级：返回原文
    assert get_translation_cache().get(text) is None  # 失败不缓存


def test_unusable_response_returns_original():
    _release_rate_limit()
    text = f"无效响应原文{time.time_ns()}"
    resp = MagicMock()
    resp.json.return_value = {"responseData": {"translatedText": "PLEASE SELECT TWO"}}
    with patch("services.translation.requests.get", return_value=resp):
        result = translate_zh_to_en(text)
    assert result == text


def test_long_prompt_truncated():
    _release_rate_limit()
    text = "长" * 2500
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["q"] = params["q"]
        return _mock_ok("ok")

    with patch("services.translation.requests.get", side_effect=fake_get):
        translate_zh_to_en(text)
    assert len(captured["q"]) == 2000


def test_cancel_during_rate_limit_wait():
    # 刚调用过 → 需要等待 1.5s；取消令牌已置位 → 立即抛取消
    _LAST_DONE[0] = time.time()
    token = CancellationToken()
    token.cancel()
    with patch("services.translation.requests.get") as mock_get:
        with pytest.raises(GenerationCancelled):
            translate_zh_to_en(f"取消测试{time.time_ns()}", token=token)
    mock_get.assert_not_called()


def test_privacy_log_does_not_leak_full_translation():
    """§23.3: 文件日志不落完整译文（仅长度+hash）。"""
    _release_rate_limit()
    logs: list[str] = []
    secret = f"这是一段绝密提示词内容{time.time_ns()}"
    with patch("services.translation.requests.get",
               return_value=_mock_ok("translated secret output")):
        translate_zh_to_en(secret, log_cb=logs.append)
    joined = "\n".join(logs)
    assert "translated secret output" not in joined
    assert "len=" in joined and "hash=" in joined


def test_cache_lru_eviction():
    cache = TranslationCache(max_size=2)
    cache.put("a", "1")
    cache.put("b", "2")
    cache.put("c", "3")   # 淘汰 a
    assert cache.get("a") is None
    assert cache.get("b") == "2"
    assert cache.get("c") == "3"
