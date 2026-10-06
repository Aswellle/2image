"""
ui/history/thumbnail.py — Viewport-aware thumbnail pipeline (UIUX P0-02/03)
─────────────────────────────────────────────────
三级结构：
    L1  PhotoImage 生命周期 —— 由调用方（sidebar._thumbs）管理
    L2  解码后 PIL 缩略图 LRU —— 本模块（工作线程安全，刷新免重解码）
    L3  源文件

缓存键 = sha256(绝对路径 + mtime_ns + 文件大小 + 缩略图尺寸)，
文件被替换后自动失效。

加载器特性：
· 优先级队列：同页卡片按可视顺序加载（页首先于页尾）
· 代号（generation）守卫：刷新后旧任务在解码前即被丢弃
· 解码与合成全部在工作线程；回调经 root.after 回主线程
"""
from __future__ import annotations

import hashlib
import itertools
import os
import queue
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable

from PIL import Image

# 缩略图底色（与既有卡片面板底色一致，保持视觉连续）
_PAD_RGB = (13, 27, 42, 255)


def cache_key(path: str, thumb_size: int) -> str:
    """文件内容敏感的缓存键：路径 + mtime_ns + 大小 + 缩略图尺寸。"""
    st = os.stat(path)
    raw = "\x1f".join((
        os.path.abspath(path), str(st.st_mtime_ns), str(st.st_size),
        str(thumb_size),
    ))
    return hashlib.sha256(raw.encode("utf-8", "surrogatepass")).hexdigest()


class PilThumbCache:
    """线程安全 LRU 缓存（键 → PIL Image）。"""

    def __init__(self, maxsize: int = 256):
        self._max = maxsize
        self._data: OrderedDict[str, Image.Image] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            img = self._data.get(key)
            if img is not None:
                self._data.move_to_end(key)
            return img

    def put(self, key: str, img: Image.Image) -> None:
        with self._lock:
            self._data[key] = img
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


def render_square(img: Image.Image, thumb_size: int) -> Image.Image:
    """缩放到 thumb_size 内并居中贴到纯色方底（与既有视觉一致）。"""
    img.thumbnail((thumb_size, thumb_size), Image.LANCZOS)
    canvas = Image.new("RGBA", (thumb_size, thumb_size), _PAD_RGB)
    ox = (thumb_size - img.width) // 2
    oy = (thumb_size - img.height) // 2
    canvas.paste(img.convert("RGBA"), (ox, oy))
    return canvas


@dataclass(order=True)
class _Job:
    priority: int
    seq: int
    gen: int = field(compare=False)
    path: str = field(compare=False)
    thumb_size: int = field(compare=False)
    on_ready: Callable = field(compare=False)
    on_missing: Callable = field(compare=False)


class ThumbnailLoader:
    """优先级缩略图加载器：解码在工作线程，回调回主线程。

    线程模型（UIUX §73）：工作线程绝不触碰 Tk —— 完成事件放入
    thread-safe 队列，由主线程的周期泵（after 30ms）取出发起回调。

    生命周期：每个实例持有常驻工作线程，**必须**在宿主窗口销毁时
    调用 shutdown()，否则线程随测试/窗口重建不断累积。
    """
    _PUMP_MS = 30
    # Sentinel handed to workers on shutdown.  It MUST be a _Job (lowest
    # priority, fully orderable): a plain object() in the heap makes
    # heappop compare it against real jobs and crash the worker thread
    # with TypeError whenever both sit in the queue at once.
    _STOP = _Job(priority=-1, seq=-1, gen=-1, path="", thumb_size=0,
                 on_ready=None, on_missing=None)

    def __init__(self, root, workers: int = 4,
                 pil_cache: PilThumbCache | None = None):
        self._root = root
        self._q: queue.PriorityQueue = queue.PriorityQueue()
        self._outq: queue.Queue = queue.Queue()
        self._pil = pil_cache or PilThumbCache()
        self._seq = itertools.count()
        self._gen = 0            # 当前代号；不一致的队列任务直接丢弃
        self._stopped = False
        self._pump_job = None
        self._threads = [
            threading.Thread(target=self._worker, daemon=True,
                             name=f"thumb-loader-{id(self)}-{i}")
            for i in range(max(1, workers))
        ]
        for t in self._threads:
            t.start()
        self._reschedule_pump()

    # ── 公共 API ─────────────────────────────────────────────
    def set_generation(self, gen: int) -> None:
        """刷新列表时递增；队列中旧代号的未开始任务将被丢弃。"""
        self._gen = gen

    def submit(self, path: str, thumb_size: int, priority: int, gen: int,
               on_ready: Callable[[Image.Image], None],
               on_missing: Callable[[], None]) -> None:
        """请求一张缩略图。on_ready/on_missing 均在主线程被调用。"""
        self._q.put(_Job(priority=priority, seq=next(self._seq), gen=gen,
                         path=path, thumb_size=thumb_size,
                         on_ready=on_ready, on_missing=on_missing))

    def clear_cache(self) -> None:
        self._pil.clear()

    def shutdown(self) -> None:
        """停止泵与工作线程并等待退出（保证 Tcl 销毁前完全静止）。

        幂等：重复调用安全。哨兵值让每个 worker 立即醒来退出，
        不依赖轮询超时。
        """
        if self._stopped:
            return
        self._stopped = True
        if self._pump_job is not None:
            try:
                self._root.after_cancel(self._pump_job)
            except Exception:
                pass
            self._pump_job = None
        for _ in self._threads:
            try:
                self._q.put(self._STOP)
            except Exception:
                pass
        for t in self._threads:
            t.join(timeout=2.0)

    # ── 主线程泵 ─────────────────────────────────────────────
    def _reschedule_pump(self):
        if self._stopped:
            return
        self._drain()
        self._pump_job = self._root.after(self._PUMP_MS, self._reschedule_pump)

    def _drain(self):
        while True:
            try:
                fn = self._outq.get_nowait()
            except queue.Empty:
                return
            try:
                fn()
            except Exception:
                pass  # 单个回调失败不阻塞队列

    # ── 工作线程（不触碰任何 Tk API）─────────────────────────
    def _worker(self):
        while True:
            try:
                job = self._q.get(timeout=0.05)
            except queue.Empty:
                if self._stopped:
                    return
                continue
            if job is self._STOP or self._stopped:
                return
            try:
                if job.gen != self._gen:
                    continue  # 过期任务：丢弃，不消耗解码资源
                if not job.path or not os.path.exists(job.path):
                    self._outq.put(job.on_missing)
                    continue
                key = cache_key(job.path, job.thumb_size)
                img = self._pil.get(key)
                if img is None:
                    img = render_square(Image.open(job.path),
                                        job.thumb_size)
                    self._pil.put(key, img)
                self._outq.put(lambda fn=job.on_ready, im=img: fn(im))
            except Exception:
                continue  # 单张失败不影响其他缩略图
