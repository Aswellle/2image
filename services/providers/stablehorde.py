"""
services/providers/stablehorde.py — StableHorde 兜底接口  v2
──────────────────────────────────────────────────────────────
批量变体失败根因：
  1. 并发提交多个任务 → 匿名 key 被限流（RC 429/503），
     现有代码直接 raise_for_status() 不处理
  2. 轮询容忍度太低：i==4 时 wait>90s 就放弃，批量时队列确实更长
  3. 图片 URL 是 R2 存储地址，有时直接 GET 会重定向或需要特定 header

v2 修复：
  1. 进程级串行锁：同一时刻只有 1 个 StableHorde 提交请求在飞
  2. 提交失败时重试（最多 3 次，指数退避）
  3. 轮询超时提升：最多等 120s 而不是 60s；wait>90s 判断延后到 i>=10
  4. 图片下载加重定向跟随 + 重试
  5. 动态调整轮询间隔（前期 3s，队列长时 5s）
"""
import threading
import time
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, validate_image_url as _validate_image_url, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "name": "StableHorde (兜底)",
    "category": "free",
    "config_key": "stablehorde_key",
}


_BASE  = "https://stablehorde.net/api/v2"
_AGENT = "TextToImageTool:11.0:local"

# ── 进程级串行锁（仅锁提交，轮询在锁外进行）────────────────────────
_SH_LOCK      = threading.Lock()
_LAST_DONE_TS = [0.0]
_MIN_INTERVAL = 3.0    # StableHorde 提交间隔（官方无明确限制，3s 保守）


def try_stablehorde(prompt: str, w: int, h: int, seed: int,
                    cfg: dict, log: Callable) -> Tuple[bytes, str]:
    api_key = cfg.get("stablehorde_key", "").strip() or "0000000000"
    anon    = api_key == "0000000000"
    log(f"► StableHorde（{'匿名' if anon else '自定义Key'}）…")

    sw = max(64, min(w, 1024) - (min(w, 1024) % 64))
    sh = max(64, min(h, 1024) - (min(h, 1024) % 64))

    sub_headers = {
        "apikey":       api_key,
        "Content-Type": "application/json",
        "Client-Agent": _AGENT,
    }
    sub_body = {
        "prompt": prompt,
        "params": {
            "width":        sw,
            "height":       sh,
            "steps":        20,
            "cfg_scale":    7.5,
            "seed":         str(seed % 2_147_483_647),
            "karras":       True,
            "sampler_name": "k_dpmpp_2m",
            "n":            1,
        },
        "models":  ["Dreamshaper 8", "stable_diffusion"],
        "shared":  True,
        "r2":      True,
        "slow_workers": True,    # 允许慢速 worker，增加成功率
    }

    # ── 串行提交（持锁，防止匿名并发被拒）──────────────────────────
    job_id = None
    with _SH_LOCK:
        gap = time.time() - _LAST_DONE_TS[0]
        if gap < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - gap)

        for attempt in range(1, 4):
            try:
                resp = _session.post(
                    f"{_BASE}/generate/async",
                    headers=sub_headers,
                    json=sub_body,
                    timeout=30)
            except requests.exceptions.ConnectionError as e:
                log(f"    提交网络错误({attempt}): {e}")
                if attempt < 3:
                    time.sleep(5)
                    continue
                break
            except requests.exceptions.Timeout:
                log(f"    提交超时({attempt})")
                if attempt < 3:
                    time.sleep(5)
                    continue
                break

            sc = resp.status_code
            log(f"    提交[{attempt}] 状态:{sc}")

            if sc == 403:
                raise ValueError(
                    "StableHorde 拒绝请求（403）\n"
                    "可能原因：API Key 被封禁或内容违规"
                )
            if sc == 401:
                raise ValueError("StableHorde API Key 无效")
            if sc in (429, 503):
                ra = resp.headers.get("Retry-After", "")
                w2 = int(ra) if ra.isdigit() else (10 * attempt)
                log(f"    限速/服务繁忙，等待 {w2}s…")
                time.sleep(w2)
                if attempt < 3:
                    continue
                break
            if sc not in (200, 202):
                try:
                    err = resp.json().get("message", resp.text[:80])
                except Exception:
                    err = resp.text[:80]
                log(f"    {sc}: {err}，重试{attempt}…")
                if attempt < 3:
                    time.sleep(5)
                    continue
                break

            job_id = resp.json().get("id")
            if job_id:
                break
            log("    响应无 id，重试…")
            if attempt < 3:
                time.sleep(3)

        _LAST_DONE_TS[0] = time.time()

    if not job_id:
        raise ValueError(
            "StableHorde 提交失败（多次重试后无 job_id）\n"
            "建议：服务繁忙，请稍后再试或换用其他接口"
        )

    log(f"  任务 {job_id[:8]}… 开始轮询…")

    # ── 轮询（锁外进行，不阻塞其他线程提交）────────────────────────
    chk_headers = {"Client-Agent": _AGENT}
    max_poll    = 40      # 40 × 动态间隔，最多约 3 分钟
    slow_count  = 0

    for i in range(max_poll):
        # 动态间隔：前 20 次 3s，之后 5s
        poll_interval = 3 if i < 20 else 5
        time.sleep(poll_interval)

        try:
            chk = _session.get(
                f"{_BASE}/generate/check/{job_id}",
                headers=chk_headers, timeout=15)
            chk.raise_for_status()
            d = chk.json()
        except Exception as e:
            log(f"  [{i+1}/{max_poll}] 轮询异常: {e}")
            continue

        if d.get("faulted"):
            raise ValueError("StableHorde 任务执行失败（faulted=true）")

        done  = d.get("done", False)
        wait  = d.get("wait_time", 0) or 0
        pos   = d.get("queue_position", "?")
        proc  = d.get("processing", 0)
        log(f"  [{i+1}/{max_poll}] done={done} 队列={pos} "
            f"预计{wait}s processing={proc}")

        if done:
            break

        # 只在早期且等待时间极长（>180s）时才放弃
        if i >= 10 and int(wait) > 180:
            slow_count += 1
            if slow_count >= 3:   # 连续 3 次都显示 >180s 才放弃
                raise TimeoutError(
                    f"StableHorde 队列持续过长（预计 {wait}s），放弃\n"
                    "建议：换用硅基流动或其他接口"
                )
    else:
        raise TimeoutError(
            f"StableHorde {max_poll * 4}s 内未完成，放弃"
        )

    # ── 获取结果 ─────────────────────────────────────────────────
    try:
        result = _session.get(
            f"{_BASE}/generate/status/{job_id}",
            headers=chk_headers, timeout=30)
        result.raise_for_status()
    except Exception as e:
        raise ValueError(f"StableHorde 获取结果失败: {e}")

    gens = result.json().get("generations", [])
    if not gens:
        raise ValueError("StableHorde 返回无 generations")

    gen     = gens[0]
    img_url = gen.get("img", "")
    model   = gen.get("model", "unknown")

    if not img_url:
        raise ValueError("StableHorde generation 无 img URL")

    log(f"  下载图片: {img_url[:60]}…")
    # 下载带重试（R2 URL 偶尔需要重定向；safe_get_image 验证所有重定向目标）
    for attempt in range(1, 4):
        try:
            data = _safe_get_image(img_url, timeout=60)
            if len(data) >= 1024:
                log(f"  ✓ StableHorde/{model} 成功，{len(data)//1024}KB")
                return data, f"StableHorde/{model}"
            log(f"    图片数据过小({len(data)}B)，重试{attempt}…")
        except Exception as e:
            log(f"    下载失败({attempt}): {e}")
            if attempt < 3:
                time.sleep(5)

    raise ValueError(f"StableHorde 图片下载失败（3次重试）: {img_url[:60]}")
