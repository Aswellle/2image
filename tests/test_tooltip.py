"""tests/test_tooltip.py — 悬浮提示共用时间常量回归。

两套提示（侧栏气泡 / 词条库说明卡）必须共用同一套延迟、帧数与
淡入曲线，否则同一种控件同一种意图会出现快慢不一。
"""
from __future__ import annotations

import pytest

from ui import tooltip


def test_timing_constants_are_sane():
    assert 200 <= tooltip.DELAY_MS <= 700
    assert tooltip.FADE_FRAMES >= 2
    assert 8 <= tooltip.FADE_FRAME_MS <= 40
    # 淡入总时长落在「能看见但不拖沓」的区间
    assert 100 <= tooltip.FADE_FRAMES * tooltip.FADE_FRAME_MS <= 300


def test_alpha_curve_starts_transparent_ends_opaque():
    assert tooltip.fade_alpha(0) == 0.0
    assert tooltip.fade_alpha(tooltip.FADE_FRAMES - 1) == pytest.approx(tooltip.MAX_ALPHA)


def test_alpha_curve_is_monotonic():
    values = [tooltip.fade_alpha(i) for i in range(tooltip.FADE_FRAMES)]
    assert all(b > a for a, b in zip(values, values[1:]))


def test_alpha_curve_is_ease_out():
    """缓出：前半程走过的比例大于线性。"""
    mid = tooltip.FADE_FRAMES // 2
    assert tooltip.fade_alpha(mid) / tooltip.MAX_ALPHA > mid / (tooltip.FADE_FRAMES - 1)


def test_alpha_never_exceeds_max():
    for step in range(tooltip.FADE_FRAMES + 5):
        assert tooltip.fade_alpha(step) <= tooltip.MAX_ALPHA


def test_both_tooltips_share_the_constants():
    from ui.phrase_panel import _PhraseTooltip
    from ui.sidebar import _Tooltip

    assert _PhraseTooltip._DELAY_MS == tooltip.DELAY_MS
    assert _PhraseTooltip._FRAMES == tooltip.FADE_FRAMES
    assert _PhraseTooltip._FRAME_MS == tooltip.FADE_FRAME_MS
    assert _PhraseTooltip._MAX_ALPHA == tooltip.MAX_ALPHA

    # 侧栏气泡的默认延迟同样来自共用常量
    import inspect

    sig = inspect.signature(_Tooltip.__init__)
    assert sig.parameters["delay_ms"].default == tooltip.DELAY_MS
