"""
services/providers/segmind.py — Segmind API 接口  v2
──────────────────────────────────────────────────────
批量变体失败根因：
  · Segmind 对同一 API Key 的并发请求严格限制（免费额度 $5）
  · 多线程并发 → 429 Rate Limited → 仅 sleep(3) → 再次并发 → 全部失败
  · SDXL 端点 enhance_style="None"（字符串）应该省略该参数
  · flux-schnell 端点不支持 samples 参数（400 错误）

v2 修复：
  1. 进程级串行锁：同一时刻只有 1 个 Segmind 请求在飞
  2. 请求之间强制等待 3s（Segmind 官方建议并发间隔）
  3. 修正 SDXL 参数：移除 enhance_style，enhance_prompt 传布尔值
  4. 修正 flux-schnell：移除不支持的 samples 参数
  5. 429 时读取 Retry-After 精确等待
  6. 超时提升至 120s
"""
import base64
import threading
import time
import requests
from typing import Callable, Tuple
from services.providers._net import SESSION as _session

PROVIDER_INFO = {
    "id": "segmind",
    "name": "Segmind (注册送$5)",
    "category": "free",
    "config_key": "segmind_key",
}

# ── 进程级串行锁 ─────────────────────────────────────────────────
_SEG_LOCK     = threading.Lock()
_LAST_DONE_TS = [0.0]
_MIN_INTERVAL = 3.0    # Segmind 建议最小并发间隔

_SEGMIND_MODELS = [
    # (endpoint, steps, guidance, use_neg, max_w, max_h, is_flux)
    ("sdxl1.0-txt2img", 30, 7.5,  True,  1024, 1024, False),
    ("flux-schnell",      4, 0.0,  False, 1024, 1024, True),
    ("sd3",              28, 7.0,  True,  1024, 1024, False),
]

_API_BASE = "https://api.segmind.com/v1"
_TIMEOUT  = 120

_NEG_PROMPT = (
    "blurry, low quality, distorted, ugly, deformed, "
    "watermark, text, logo, bad anatomy, extra limbs"
)


def try_segmind(prompt: str, w: int, h: int, seed: int,
                cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("segmind_key", "").strip()
    if not key:
        raise ValueError(
            "需要 Segmind API Key！\n"
            "注册免费获赠 $5 额度：https://www.segmind.com"
        )

    hq_mode  = bool(cfg.get("variant_hq", False))
    mode_tag = "HQ变体" if hq_mode else "标准"
    log(f"► Segmind API（注册送 $5 额度）[{mode_tag}]…")

    headers = {
        "x-api-key":    key,
        "Content-Type": "application/json",
    }

    def snap(v: int, mx: int) -> int:
        return min(max(512, (v // 64) * 64), mx)

    for endpoint, steps, guidance, use_neg, max_w, max_h, is_flux in _SEGMIND_MODELS:
        # HQ 模式适当增加步数（FLUX 步数有上限，不超 8）
        use_steps = steps + (4 if hq_mode and not is_flux else
                             (2 if hq_mode and is_flux else 0))
        sw  = snap(w, max_w)
        sh  = snap(h, max_h)
        url = f"{_API_BASE}/{endpoint}"
        log(f"  模型: {endpoint}  {sw}×{sh}  steps={use_steps}")

        payload: dict = {
            "prompt": prompt,
            "width":  sw,
            "height": sh,
            "num_inference_steps": use_steps,
            "seed":   seed % 2_147_483_647,
            "img_format": "png",
        }
        if guidance > 0:
            payload["guidance_scale"] = guidance
        if use_neg:
            payload["negative_prompt"] = _NEG_PROMPT

        # SDXL 特有参数（修复：移除 enhance_style="None"，改为正确布尔值）
        if "sdxl" in endpoint:
            payload["sampler"]        = "dpmpp_2m"
            payload["scheduler"]      = "karras"
            payload["enhance_prompt"] = hq_mode   # 布尔值

        # FLUX：不传 samples（该端点不支持）
        if not is_flux:
            payload["samples"] = 1

        result = None

        # ── 持锁串行 ─────────────────────────────────────────────
        with _SEG_LOCK:
            gap = time.time() - _LAST_DONE_TS[0]
            if gap < _MIN_INTERVAL:
                time.sleep(_MIN_INTERVAL - gap)

            for attempt in range(1, 4):
                try:
                    resp = _session.post(url, headers=headers,
                                         json=payload, timeout=_TIMEOUT)
                except requests.exceptions.ConnectionError as e:
                    log(f"    网络错误: {e}")
                    break
                except requests.exceptions.Timeout:
                    log(f"    超时第{attempt}次")
                    if attempt < 3:
                        time.sleep(10 * attempt)
                        continue
                    break

                sc = resp.status_code
                log(f"    [{attempt}] 状态:{sc}")

                if sc == 401:
                    raise ValueError("Segmind API Key 无效，请检查设置")
                if sc == 402:
                    raise ValueError(
                        "Segmind 额度不足！\n"
                        "请前往 https://www.segmind.com 查看余额。"
                    )
                if sc == 429:
                    ra = resp.headers.get("Retry-After", "")
                    w2 = int(ra) if ra.isdigit() else 10
                    log(f"    429 限速，等待 {w2}s…")
                    time.sleep(w2)
                    if attempt < 3:
                        continue
                    break
                if sc in (400, 422):
                    try:
                        err = resp.json().get("error", resp.text[:120])
                    except Exception:
                        err = resp.text[:120]
                    log(f"    参数错误: {err}，换模型…")
                    break
                if sc != 200:
                    log(f"    {sc}，换模型…")
                    break

                # ── 解析响应 ────────────────────────────────────
                ct = resp.headers.get("Content-Type", "")
                if "image" in ct:
                    log(f"  ✓ Segmind/{endpoint} 成功（直接图片）")
                    result = (resp.content, f"Segmind/{endpoint}")
                    break

                if "json" in ct or ct == "":
                    try:
                        j = resp.json()
                    except Exception:
                        log("    无法解析 JSON，换模型…")
                        break

                    b64 = (j.get("image") or j.get("b64_json")
                           or j.get("base64"))
                    if b64:
                        try:
                            img = base64.b64decode(b64)
                            log(f"  ✓ Segmind/{endpoint} 成功（base64）")
                            result = (img, f"Segmind/{endpoint}")
                        except Exception as de:
                            log(f"    base64 解码失败: {de}，换模型…")
                        break

                    images = j.get("images", [])
                    if images:
                        try:
                            img = base64.b64decode(images[0])
                            log(f"  ✓ Segmind/{endpoint} 成功（images[]）")
                            result = (img, f"Segmind/{endpoint}")
                        except Exception as de:
                            log(f"    images[0] 解码失败: {de}，换模型…")
                        break

                    err = j.get("error", j.get("message", str(j)[:120]))
                    log(f"    未知响应: {err}，换模型…")
                    break

                log(f"    未知 Content-Type={ct}，换模型…")
                break

            _LAST_DONE_TS[0] = time.time()

        if result:
            return result

    raise ValueError(
        "Segmind 所有模型均失败\n"
        "请检查 API Key 或访问 https://www.segmind.com 查看服务状态。"
    )
