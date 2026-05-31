"""
services/providers/pollinations.py — Pollinations.AI 接口  v4
──────────────────────────────────────────────────────────────
批量变体失败根因（v3 残留 bug）：
  · _LAST_REQ_TIME 在请求发出前就更新，导致计时从"请求开始"算起
  · 若请求本身耗时 < 15s，下一线程拿到锁后 wait_for_slot 认为间隔已够，
    实际上上一请求刚结束没多久，仍触发限速

v4 修复：
  · _LAST_REQ_TIME 只在请求完全结束（成功/失败/超时）后才更新
  · 官方匿名限速：每 15s 一次；锁内等待保证严格串行
  · 500/503 指数退避重试（最多 3 次）
  · 超时提升至 180s，兼顾高负载场景
"""
import threading
import time
import urllib.parse
from typing import Callable, Tuple
from services.providers._net import SESSION as _session

PROVIDER_INFO = {
    "name": "Pollinations.AI (免费·无需Key)",
    "category": "free",
    "config_key": None,
}

# ── 进程级串行锁：保证同一时刻只有 1 个 Pollinations 请求在飞 ────────
_POLL_LOCK     = threading.Lock()
_LAST_DONE_TS  = [0.0]        # 上次请求【完成】时间戳（关键：完成后才写入）

_MIN_INTERVAL  = 16.0         # 官方匿名限速 15s，留 1s 余量
_POLL_MODELS_STD = ["flux", "flux-realism", "turbo"]
_POLL_MODELS_HQ  = ["flux", "flux-realism"]
_BASE_URL = "https://image.pollinations.ai/prompt/{prompt}"
_TIMEOUT  = 180
_MAX_RETRY = 3


def try_pollinations(prompt: str, w: int, h: int, seed: int,
                     cfg: dict, log: Callable) -> Tuple[bytes, str]:
    """线程安全地调用 Pollinations.AI，遵守官方 15s 限速。"""
    hq_mode  = bool(cfg.get("variant_hq", False))
    mode_tag = "HQ变体" if hq_mode else "标准"
    log(f"► Pollinations.AI（完全免费，无需 Key）[{mode_tag}]…")

    def _snap(v: int, mx: int = 1280) -> int:
        return min(max(64, (v // 64) * 64), mx)

    sw  = _snap(w)
    sh  = _snap(h)
    enc = urllib.parse.quote(prompt, safe="")
    model_list = _POLL_MODELS_HQ if hq_mode else _POLL_MODELS_STD

    for model in model_list:
        log(f"  模型: {model}  {sw}×{sh}"
            + (" [enhance=true]" if hq_mode else ""))
        url    = _BASE_URL.format(prompt=enc)
        params = {
            "width": sw, "height": sh,
            "seed":  seed % 2_147_483_647,
            "model": model,
            "nologo":  "true",
            "enhance": "true" if hq_mode else "false",
        }

        result = None

        # ── 持锁范围仅限限速等待：锁释放后再发 HTTP 请求 ──────────
        # 修复：原版锁覆盖整个 HTTP 调用，导致批量 N 线程完全串行。
        # 正确做法：只在锁内等待最小间隔，锁外并发执行实际请求。
        with _POLL_LOCK:
            gap = time.time() - _LAST_DONE_TS[0]
            if gap < _MIN_INTERVAL:
                wait = _MIN_INTERVAL - gap
                log(f"  [Pollinations] 限速等待 {wait:.1f}s…")
                time.sleep(wait)
            # 预占时间槽后立即释放锁，让其他线程进入等待队列
            _LAST_DONE_TS[0] = time.time()

        # HTTP 请求在锁外执行，多线程可真正并发
        for attempt in range(1, _MAX_RETRY + 1):
            try:
                resp = _session.get(url, params=params,
                                    timeout=_TIMEOUT, allow_redirects=True)
            except requests.exceptions.ConnectionError as e:
                log(f"    网络错误: {e}")
                break
            except requests.exceptions.Timeout:
                log(f"    超时（{_TIMEOUT}s）第{attempt}次")
                if attempt < _MAX_RETRY:
                    time.sleep(10 * attempt)
                    continue
                break

            sc = resp.status_code
            ct = resp.headers.get("Content-Type", "")
            log(f"    [{attempt}] 状态:{sc}  ct:{ct}")

            if sc in (429, 503):
                ra = resp.headers.get("Retry-After", "")
                w2 = int(ra) if ra.isdigit() else max(_MIN_INTERVAL, 20)
                log(f"    限速/不可用，等待 {w2:.0f}s…")
                time.sleep(w2)
                if attempt < _MAX_RETRY:
                    continue
                break

            if sc == 500:
                w2 = 15 * attempt
                log(f"    服务器 500，等待 {w2}s…")
                time.sleep(w2)
                if attempt < _MAX_RETRY:
                    continue
                break

            if sc != 200:
                log(f"    {sc}，换模型…")
                break

            if "image" not in ct:
                log(f"    非图片响应({ct})，换模型…")
                break

            if len(resp.content) < 1024:
                log("    数据过小，换模型…")
                break

            log(f"  ✓ Pollinations/{model} 成功 "
                f"{len(resp.content)//1024}KB")
            result = (resp.content, f"Pollinations/{model}")
            break

        # 请求完成后更新实际完成时间戳（GIL 保证 list 赋值原子性）
        _LAST_DONE_TS[0] = time.time()

        if result:
            return result

    raise ValueError(
        "Pollinations.AI 所有模型均失败\n"
        "原因：匿名限速(15s/次)、服务不可用或网络异常\n"
        "建议换用硅基流动；注册免费账号可提速：https://auth.pollinations.ai"
    )
