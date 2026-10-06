"""tests/test_thumbnail.py — 缩略图管线回归（UIUX P0-02/03）。

覆盖：cache_key 内容敏感性、PilThumbCache LRU、render_square、
ThumbnailLoader 优先级/代号取消/回调线程调度。
"""
from __future__ import annotations

import os
import time

import pytest
from PIL import Image

from ui.history.thumbnail import (PilThumbCache, ThumbnailLoader,
                                  cache_key, render_square)


@pytest.fixture
def png_file(tmp_path):
    p = tmp_path / "img.png"
    Image.new("RGB", (300, 200), (200, 30, 30)).save(p)
    return str(p)


# ── cache_key ────────────────────────────────────────────────
def test_cache_key_stable(png_file):
    assert cache_key(png_file, 90) == cache_key(png_file, 90)


def test_cache_key_sensitive_to_thumb_size(png_file):
    assert cache_key(png_file, 90) != cache_key(png_file, 120)


def test_cache_key_sensitive_to_mtime(png_file):
    k1 = cache_key(png_file, 90)
    old = os.stat(png_file).st_atime_ns
    past = old - 10_000_000_000
    os.utime(png_file, ns=(past, past))
    assert cache_key(png_file, 90) != k1


# ── PilThumbCache ────────────────────────────────────────────
def test_lru_eviction():
    c = PilThumbCache(maxsize=2)
    c.put("a", Image.new("RGB", (4, 4)))
    c.put("b", Image.new("RGB", (4, 4)))
    c.put("c", Image.new("RGB", (4, 4)))
    assert c.get("a") is None      # 最旧被逐出
    assert c.get("b") is not None
    assert c.get("c") is not None
    assert len(c) == 2


def test_lru_touch_refreshes_order():
    c = PilThumbCache(maxsize=2)
    c.put("a", Image.new("RGB", (4, 4)))
    c.put("b", Image.new("RGB", (4, 4)))
    c.get("a")                     # 触摸 a，使其新于 b
    c.put("c", Image.new("RGB", (4, 4)))
    assert c.get("a") is not None  # a 仍在
    assert c.get("b") is None      # b 被逐出


def test_cache_clear():
    c = PilThumbCache()
    c.put("k", Image.new("RGB", (4, 4)))
    c.clear()
    assert len(c) == 0


# ── render_square ────────────────────────────────────────────
def test_render_square_dims_and_padding():
    img = Image.new("RGB", (300, 100), (255, 0, 0))
    out = render_square(img, 90)
    assert out.size == (90, 90)
    assert out.mode == "RGBA"
    # 底色像素（左上角为 padding 区）
    assert out.getpixel((1, 1))[:3] == (13, 27, 42)


def test_render_square_idempotent_on_small(png_file):
    out = render_square(Image.open(png_file), 90)
    assert out.size == (90, 90)


# ── ThumbnailLoader ──────────────────────────────────────────
def _pump(root, seconds=2.0):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.02)


@pytest.fixture
def make_loader(tk_root):
    """创建 loader 并保证测试结束时 worker 先停、根窗口后毁。"""
    loaders = []

    def _make(**kw):
        ld = ThumbnailLoader(tk_root, **kw)
        loaders.append(ld)
        return ld

    yield _make
    for ld in loaders:
        ld.shutdown()  # 内部 join：worker 全部退出后才销毁根窗口
    time.sleep(0.05)


def test_loader_ready_callback(tk_root, make_loader, png_file):
    loader = make_loader(workers=1)
    results = []
    loader.set_generation(1)
    loader.submit(png_file, 90, 0, 1,
                  on_ready=results.append, on_missing=lambda: results.append("missing"))
    _pump(tk_root)
    assert results and results[0] != "missing"
    assert results[0].size == (90, 90)


def test_loader_missing_file(tk_root, make_loader, tmp_path):
    loader = make_loader(workers=1)
    results = []
    loader.set_generation(1)
    loader.submit(str(tmp_path / "nope.png"), 90, 0, 1,
                  on_ready=results.append, on_missing=lambda: results.append("missing"))
    _pump(tk_root)
    assert results == ["missing"]


def test_loader_stale_generation_dropped(tk_root, make_loader, png_file):
    """刷新后旧代号任务在解码前被丢弃。"""
    loader = make_loader(workers=1)
    results = []
    loader.set_generation(2)
    loader.submit(png_file, 90, 0, 1,   # 旧代号 1
                  on_ready=results.append, on_missing=lambda: results.append("missing"))
    _pump(tk_root, 0.8)
    assert results == []


def test_loader_uses_l2_cache(tk_root, make_loader, png_file):
    loader = make_loader(workers=1)
    results = []
    loader.set_generation(1)
    for _ in range(3):
        loader.submit(png_file, 90, 0, 1,
                      on_ready=results.append, on_missing=lambda: None)
    _pump(tk_root)
    assert len(results) == 3
    assert len(loader._pil) == 1     # 三次请求共用一份解码
    assert results[0] is results[1]  # 同一 PIL 对象（L2 命中）


def test_loader_shutdown_with_pending_jobs_is_crash_free(tk_root, make_loader,
                                                         png_file):
    """Regression: shutdown() used to push a bare object() sentinel into
    the PriorityQueue; with workers busy and jobs still queued, heappop
    then compared the unorderable sentinel against _Job and killed the
    worker threads with TypeError.  The sentinel is now a lowest-priority
    _Job, so mixed-queue shutdown drains cleanly."""
    loader = make_loader(workers=4)
    loader.set_generation(1)
    for i in range(40):   # far more work than 4 workers can drain at once
        loader.submit(png_file, 90, i, 1,
                      on_ready=lambda im: None, on_missing=lambda: None)
    loader.shutdown()     # sentinel lands while real jobs are queued
    for t in loader._threads:
        assert not t.is_alive()
