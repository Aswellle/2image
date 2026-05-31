"""
services/providers/huggingface.py — HuggingFace Inference API  v2
──────────────────────────────────────────────────────────────────
批量变体失败根因：
  · HF 免费账号对同一 token 的并发推理请求限制极严（实测同时只允许 1 个）
  · 多线程并发 → 全部 429 → sleep(3) → 再次并发 → 雪崩循环
  · FLUX.1-schnell 在 HF router 上要求 inputs 是纯文本，
    不能放 parameters.width/height（部分路由不支持 → 500/422）

v2 修复：
  1. 进程级串行锁：同一时刻只有 1 个 HF 请求在飞，彻底消除并发
  2. 429 指数退避：读取 Retry-After 精确等待
  3. FLUX 模型参数修正：width/height/steps 放在顶层 parameters，
     同时兼容不同 router 路由的响应格式
  4. 超时提升至 300s（HF 免费推理队列较长）
  5. 移除 sdxl-turbo（HF router 对其限制严，经常 503）
"""
import base64
import threading
import time
import requests
# Session with connection pooling for HTTP keep-alive
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(
    pool_connections=2, pool_maxsize=4, max_retries=1)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)
import ipaddress
from urllib.parse import urlparse
from typing import Callable, Tuple

PROVIDER_INFO = {
    "name": "HuggingFace (备用)",
    "category": "free",
    "config_key": "hf_token",
    "try_fn": "try_hf_inference",
}


def _validate_image_url(url: str) -> bool:
    """Block non-HTTPS URLs and internal/reserved IP ranges to prevent SSRF."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("https",):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            return False
    except ValueError:
        pass
    return True


def _safe_error_text(resp) -> str:
    """Extract safe error message from API response, avoiding raw body leakage."""
    try:
        body = resp.json()
        err = body.get("error", {})
        if isinstance(err, dict):
            return err.get("message", "") or str(err)[:150]
        if isinstance(err, str):
            return err[:150]
        return body.get("message", "") or str(body)[:150]
    except Exception:
        return f"HTTP {resp.status_code}"
# ── 进程级串行锁：保证同一时刻只有 1 个 HF 请求在飞 ─────────────────
_HF_LOCK      = threading.Lock()
_LAST_DONE_TS = [0.0]
_MIN_INTERVAL = 2.0       # HF 每次请求之间最少等 2s（宽松，主要靠锁串行）

# 模型列表（已移除 sdxl-turbo 和 sd-v1-5，均在 HF router 上不稳定）
HF_MODELS = [
    # (model_id,                                  steps, guidance, max_w, max_h)
    ("black-forest-labs/FLUX.1-schnell",            4,   0.0,  1024, 1024),
    ("stabilityai/stable-diffusion-xl-base-1.0",   20,   7.5,  1024, 1024),
    ("stabilityai/stable-diffusion-2-1",           20,   7.5,   768,  768),
]
HF_HQ_MODELS = [
    ("black-forest-labs/FLUX.1-schnell",            8,   0.0,  1024, 1024),
    ("stabilityai/stable-diffusion-xl-base-1.0",   30,   8.0,  1024, 1024),
]

_TIMEOUT = 300     # HF 免费推理队列长，需要足够的超时


def try_hf_inference(prompt: str, w: int, h: int, seed: int,
                     cfg: dict, log: Callable) -> Tuple[bytes, str]:
    token = cfg.get("hf_token", "").strip()
    if not token:
        raise ValueError("需要 HuggingFace Token，请在「⚙ 设置」中填写")

    hq_mode    = bool(cfg.get("variant_hq", False))
    model_list = HF_HQ_MODELS if hq_mode else HF_MODELS
    mode_tag   = "HQ变体" if hq_mode else "标准"
    log(f"► HuggingFace Inference API [{mode_tag}]…")

    headers = {
        "Authorization":    f"Bearer {token}",
        "Content-Type":     "application/json",
        "x-wait-for-model": "true",   # 让服务端排队而不是立刻返回 503
        "x-use-cache":      "false",
    }

    def snap(v: int, mx: int) -> int:
        return max(64, min(v, mx) // 64 * 64)

    for model_id, steps, guidance, max_w, max_h in model_list:
        mw = snap(w, max_w)
        mh = snap(h, max_h)
        sn = model_id.split("/")[-1]
        log(f"  模型: {sn}  {mw}×{mh}  steps={steps}")

        url = (f"https://router.huggingface.co/hf-inference/models/{model_id}")

        # parameters 结构：FLUX 和 SDXL 参数位置相同
        params_dict: dict = {
            "width":               mw,
            "height":              mh,
            "num_inference_steps": steps,
            "seed":                seed % 2_147_483_647,
        }
        if guidance > 0:
            params_dict["guidance_scale"] = guidance
        # HQ 模式加 negative_prompt（SDXL 支持，FLUX 忽略）
        if hq_mode and guidance > 0:
            params_dict["negative_prompt"] = (
                "blurry, low quality, distorted, ugly, watermark, "
                "deformed, extra limbs, bad anatomy"
            )
        body = {"inputs": prompt, "parameters": params_dict}

        result = None

        # ── 持锁串行 ─────────────────────────────────────────────
        with _HF_LOCK:
            gap = time.time() - _LAST_DONE_TS[0]
            if gap < _MIN_INTERVAL:
                time.sleep(_MIN_INTERVAL - gap)

            for attempt in range(1, 4):   # 最多 3 次重试
                try:
                    resp = _session.post(url, headers=headers,
                                         json=body, timeout=_TIMEOUT)
                except requests.exceptions.ConnectionError as e:
                    log(f"    网络错误: {e}")
                    break
                except requests.exceptions.Timeout:
                    log(f"    超时（{_TIMEOUT}s）第{attempt}次")
                    if attempt < 3:
                        time.sleep(15 * attempt)
                        continue
                    break

                sc = resp.status_code
                log(f"    [{attempt}] 状态:{sc}")

                if sc == 401:
                    raise ValueError("HuggingFace Token 无效或已过期")
                if sc == 403:
                    raise ValueError("HuggingFace Token 无 Inference 权限")
                if sc in (404, 410):
                    log(f"    {sc} 模型不可用，换模型…")
                    break

                if sc == 429:
                    # 精确读取 Retry-After
                    ra = resp.headers.get("Retry-After", "")
                    w2 = int(ra) if ra.isdigit() else 30
                    log(f"    429 限速，等待 {w2}s…")
                    time.sleep(w2)
                    if attempt < 3:
                        continue
                    break

                if sc == 503:
                    # x-wait-for-model=true 情况下 503 表示模型仍在加载
                    log(f"    503 模型加载中，等待 20s…")
                    time.sleep(20)
                    if attempt < 3:
                        continue
                    break

                if sc not in (200, 201):
                    # 尝试读取错误详情
                    try:
                        err_body = resp.json()
                        err_msg  = err_body.get("error", _safe_error_text(resp))
                    except Exception:
                        err_msg = _safe_error_text(resp)
                    log(f"    {sc}: {err_msg}，换模型…")
                    break

                # ── 解析响应 ────────────────────────────────────
                ct = resp.headers.get("Content-Type", "")

                # 直接图片二进制
                if "image" in ct:
                    log(f"  ✓ HuggingFace/{sn} 成功（直接图片）")
                    result = (resp.content, f"HuggingFace/{sn}")
                    break

                # JSON 格式
                if "json" in ct or ct == "":
                    try:
                        j = resp.json()
                    except Exception:
                        log("    非 JSON，换模型…")
                        break

                    # 格式 A：list[{"generated_image"|"image"|"b64_json": ...}]
                    if isinstance(j, list) and j:
                        item = j[0]
                        for key in ("generated_image", "image", "b64_json"):
                            val = item.get(key)
                            if val:
                                try:
                                    img = base64.b64decode(val)
                                    log(f"  ✓ HuggingFace/{sn} 成功（list.{key}）")
                                    result = (img, f"HuggingFace/{sn}")
                                except Exception:
                                    pass
                                break
                        if result:
                            break

                    # 格式 B：{"images": [{"url": ...}]}
                    if isinstance(j, dict):
                        imgs = j.get("images", [])
                        if imgs and imgs[0].get("url"):
                            if not _validate_image_url(imgs[0]['url']):
                                raise RuntimeError(f"Blocked unsafe image URL: {imgs[0]['url'][:100]}")
                            ir = _session.get(imgs[0]['url'], timeout=60)
                            ir.raise_for_status()
                            log(f"  ✓ HuggingFace/{sn} 成功（images.url）")
                            result = (ir.content, f"HuggingFace/{sn}")
                            break

                        # 格式 C：{"data": [{"b64_json"|"url": ...}]}
                        data = j.get("data", [])
                        if data:
                            if data[0].get("b64_json"):
                                img = base64.b64decode(data[0]["b64_json"])
                                log(f"  ✓ HuggingFace/{sn} 成功（data.b64_json）")
                                result = (img, f"HuggingFace/{sn}")
                                break
                            if data[0].get("url"):
                                if not _validate_image_url(data[0]['url']):
                                    raise RuntimeError(f"Blocked unsafe image URL: {data[0]['url'][:100]}")
                                ir = _session.get(data[0]['url'], timeout=60)
                                ir.raise_for_status()
                                log(f"  ✓ HuggingFace/{sn} 成功（data.url）")
                                result = (ir.content, f"HuggingFace/{sn}")
                                break

                        err_info = j.get("error", str(j)[:100])
                        log(f"    未知 JSON: {err_info}，换模型…")
                        break

                    log("    未识别 JSON 格式，换模型…")
                    break

                log(f"    未知 Content-Type={ct}，换模型…")
                break

            # 请求完成后更新时间戳（无论成功失败）
            _LAST_DONE_TS[0] = time.time()

        if result:
            return result

    raise ValueError(
        "所有 HuggingFace 模型均失败\n"
        "原因：免费账号并发限制或推理配额耗尽\n"
        "建议：换用硅基流动（速度更快、更稳定）"
    )
