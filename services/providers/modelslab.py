"""
services/providers/modelslab.py — ModelsLab API 接口  v2
──────────────────────────────────────────────────────────
批量变体失败根因：
  1. 并发：多线程同时提交 → 触发并发限制 → 返回 error 状态
  2. 轮询超时太短：_MAX_POLL=12×5s=60s，ModelsLab 免费 tier 实际
     处理时间可达 2~5 分钟（FLUX 尤甚）
  3. seed 参数传整数，ModelsLab 要求字符串类型
  4. guidance_scale 传 Python float，其余参数用 str → 混合类型
     在某些模型上触发 422 参数验证错误
  5. flux 模型的 guidance_scale 在 ModelsLab 上要传 1.0（不支持 <1）

v2 修复：
  1. 进程级串行锁（_ML_LOCK）：同一时刻只有 1 个 ModelsLab 请求在飞
  2. 轮询延长至 36×10s = 360s（6分钟），适应免费 tier 排队时间
  3. 所有数值参数统一为 str 类型（ModelsLab API 规范）
  4. flux 模型 guidance_scale 设为 "7.5"（兼容最广泛）
  5. 请求完成后才更新时间戳
  6. 网络下载超时提升至 120s
"""
import threading
import time
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, validate_image_url as _validate_image_url, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "name": "ModelsLab (免费100次/天)",
    "category": "free",
    "config_key": "modelslab_key",
}


# ── 进程级串行锁 ─────────────────────────────────────────────────
_ML_LOCK      = threading.Lock()
_LAST_DONE_TS = [0.0]
_MIN_INTERVAL = 2.0     # ModelsLab 限速相对宽松，2s 间隔足够

_API_URL   = "https://modelslab.com/api/v6/images/text2img"
_FETCH_URL = "https://modelslab.com/api/v6/images/fetch"
_TIMEOUT   = 90
_MAX_POLL  = 36    # 36 × 10s = 360s（6分钟），适应免费 tier 长队列
_POLL_INTERVAL = 10

# 模型列表：(model_id, steps, guidance_scale_str, has_neg)
# 注意：所有数值参数统一为 str，guidance_scale 也是
_ML_MODELS = [
    ("flux",                  "20", "7.5",  False),
    ("sdxl",                  "30", "7.5",  True),
    ("realistic-vision-v51",  "30", "7.0",  True),
    ("sd-1.5",                "25", "7.0",  True),
]
_ML_HQ_MODELS = [
    ("flux",                  "25", "7.5",  False),
    ("sdxl",                  "35", "8.0",  True),
    ("realistic-vision-v51",  "35", "7.5",  True),
]

_HQ_NEGATIVE = (
    "ugly, deformed, noisy, blurry, distorted, out of focus, "
    "bad anatomy, extra limbs, poorly drawn face, poorly drawn hands, "
    "missing fingers, extra fingers, watermark, text, logo"
)


def _download_image(url: str, log: Callable) -> bytes:
    """下载图片，带重试。safe_get_image 验证 URL 及所有重定向目标。"""
    for attempt in range(1, 4):
        try:
            data = _safe_get_image(url, timeout=120)
            if len(data) >= 1024:
                return data
            log(f"    下载数据过小（{len(data)}B），重试{attempt}…")
        except Exception as e:
            log(f"    下载失败({attempt}): {e}")
            if attempt < 3:
                time.sleep(5)
    raise ValueError(f"图片下载失败：{url[:80]}")


def try_modelslab(prompt: str, w: int, h: int, seed: int,
                  cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("modelslab_key", "").strip()
    if not key:
        raise ValueError(
            "需要 ModelsLab API Key！\n"
            "免费注册（每天 100 次）：https://modelslab.com"
        )

    hq_mode    = bool(cfg.get("variant_hq", False))
    mode_tag   = "HQ变体" if hq_mode else "标准"
    model_list = _ML_HQ_MODELS if hq_mode else _ML_MODELS
    log(f"► ModelsLab（免费 100次/天）[{mode_tag}]…")

    def snap(v: int, mx: int = 1024) -> int:
        return min(max(256, (v // 64) * 64), mx)

    sw = snap(w)
    sh = snap(h)

    for model_id, steps_str, guidance_str, has_neg in model_list:
        log(f"  模型: {model_id}  {sw}×{sh}  steps={steps_str}")

        # ── 所有数值参数统一为字符串（ModelsLab API 要求）────────
        payload: dict = {
            "key":                 key,
            "model_id":            model_id,
            "prompt":              prompt,
            "width":               str(sw),
            "height":              str(sh),
            "samples":             "1",
            "num_inference_steps": steps_str,
            "guidance_scale":      guidance_str,
            "seed":                str(seed % 2_147_483_647),
            "safety_checker":      "no",
            "enhance_prompt":      "yes" if hq_mode else "no",
            "base64":              "no",
        }
        if has_neg:
            payload["negative_prompt"] = _HQ_NEGATIVE

        result = None

        # ── 持锁串行 ─────────────────────────────────────────────
        with _ML_LOCK:
            gap = time.time() - _LAST_DONE_TS[0]
            if gap < _MIN_INTERVAL:
                time.sleep(_MIN_INTERVAL - gap)

            try:
                resp = _session.post(_API_URL, json=payload, timeout=_TIMEOUT)
            except requests.exceptions.ConnectionError as e:
                log(f"    网络错误: {e}，换模型…")
                _LAST_DONE_TS[0] = time.time()
                continue
            except requests.exceptions.Timeout:
                log("    提交超时，换模型…")
                _LAST_DONE_TS[0] = time.time()
                continue

            _LAST_DONE_TS[0] = time.time()
            sc = resp.status_code
            log(f"    提交状态:{sc}")

            if sc == 401:
                raise ValueError("ModelsLab API Key 无效，请检查设置")
            if sc == 402:
                raise ValueError("ModelsLab 免费额度已用尽，请等明天重置")
            if sc == 429:
                ra = resp.headers.get("Retry-After", "")
                w2 = int(ra) if ra.isdigit() else 10
                log(f"    429 限速，等待 {w2}s…")
                time.sleep(w2)
                # 限速直接换模型，不重试（已用锁保证串行，重试意义不大）
                continue
            if sc not in (200, 201):
                log(f"    {sc}，换模型…")
                continue

            try:
                j = resp.json()
            except Exception:
                log("    无法解析 JSON，换模型…")
                continue

            status = j.get("status", "")

            # ── 状态：success → 直接下载 ─────────────────────────
            if status == "success":
                outputs = j.get("output", [])
                if not outputs:
                    log("    output 为空，换模型…")
                    continue
                try:
                    img_bytes = _download_image(outputs[0], log)
                    log(f"  ✓ ModelsLab/{model_id} 成功，"
                        f"{len(img_bytes)//1024}KB")
                    result = (img_bytes, f"ModelsLab/{model_id}")
                except Exception as e:
                    log(f"    下载失败: {e}，换模型…")
                continue

            # ── 状态：processing → 轮询（在锁外轮询，避免长时间占锁）─
            if status in ("processing", "queued"):
                fetch_id = j.get("id")
                if not fetch_id:
                    # 有些版本在 future_links 里
                    fl = j.get("future_links", [])
                    fetch_id = fl[0] if fl else None
                if not fetch_id:
                    log("    无法获取轮询 ID，换模型…")
                    continue

                log(f"    队列处理中（id={fetch_id}），开始轮询（最多{_MAX_POLL * _POLL_INTERVAL}s）…")
                # 先释放锁，在锁外轮询（轮询时间可能很长）
        # ── 锁外轮询 ─────────────────────────────────────────────
        if status in ("processing", "queued") and fetch_id:
            poll_result = None
            for i in range(_MAX_POLL):
                time.sleep(_POLL_INTERVAL)
                try:
                    fr  = _session.post(
                        _FETCH_URL,
                        json={"key": key, "request_id": str(fetch_id)},
                        timeout=30)
                    fj  = fr.json()
                except Exception as e:
                    log(f"    [{i+1}/{_MAX_POLL}] 轮询异常: {e}")
                    continue

                fs = fj.get("status", "")
                log(f"    [{i+1}/{_MAX_POLL}] status={fs}")

                if fs == "success":
                    fout = fj.get("output", [])
                    if fout:
                        try:
                            img_bytes = _download_image(fout[0], log)
                            log(f"  ✓ ModelsLab/{model_id} 轮询成功，"
                                f"{len(img_bytes)//1024}KB")
                            poll_result = (img_bytes, f"ModelsLab/{model_id}")
                        except Exception as e:
                            log(f"    轮询下载失败: {e}")
                    break
                if fs in ("failed", "error"):
                    log(f"    生成失败: {fj.get('message', fj.get('error', ''))}")
                    break
            else:
                log(f"    {_MAX_POLL * _POLL_INTERVAL}s 内未完成，换模型…")

            if poll_result:
                return poll_result
            continue

        # ── 其他错误状态 ──────────────────────────────────────────
        if result is None:
            err = j.get("message", j.get("error", str(j)[:120]))
            log(f"    错误状态 '{status}': {err}，换模型…")
            continue

        if result:
            return result

    raise ValueError(
        "ModelsLab 所有模型均失败\n"
        "请检查 API Key 或访问 https://modelslab.com 查看服务状态。"
    )
