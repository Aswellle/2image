"""
services/providers/cloudflare_ai.py — Cloudflare Workers AI 接口
──────────────────────────────────────────────────────────────────
Cloudflare Workers AI 是 Cloudflare 提供的免费 AI 推理服务。
  · 免费额度：每天 10,000 neurons（约 10~20 张全分辨率图片）
  · 无需信用卡，注册 Cloudflare 账号即可
  · 支持模型：FLUX.1-schnell（12B，最高质量）、SDXL-base、SDXL-Lightning
  · 注册地址：https://dash.cloudflare.com
  · 文档：https://developers.cloudflare.com/workers-ai/models/

配置参数：
  cf_account_id   — Cloudflare 账户 ID（dashboard 右侧栏可找到）
  cf_api_token    — API Token（需要 Workers AI Read 权限）
  获取 Token：https://dash.cloudflare.com/profile/api-tokens
    → Create Token → 选择 "Workers AI (Read)" 模板

API 响应：直接返回 base64 编码的图片数据（无需二次下载）
"""
import base64
import time
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text

PROVIDER_INFO = {
    "name": "Cloudflare AI (免费1万次/天)",
    "category": "free",
    "config_key": "cf_account_id",
}



_API_BASE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
_TIMEOUT  = 60

# 模型列表（按质量排序）
# FLUX.1-schnell：12B 参数，质量最高，速度约 2-5s
# SDXL-base：质量好，生成速度稳定
# SDXL-Lightning：最快，4步蒸馏，质量稍次
_CF_MODELS = [
    # (model_path,                                              steps, guidance, max_sz)
    ("@cf/black-forest-labs/flux-1-schnell",                    8,     0.0,    1024),
    ("@cf/stabilityai/stable-diffusion-xl-base-1.0",            20,    7.5,    1024),
    ("@cf/bytedance/stable-diffusion-xl-lightning",              4,     0.0,    1024),
]

# HQ 模式：优先 FLUX，跳过 Lightning
_CF_HQ_MODELS = [
    ("@cf/black-forest-labs/flux-1-schnell",                    8,     0.0,    1024),
    ("@cf/stabilityai/stable-diffusion-xl-base-1.0",            30,    8.0,    1024),
]


def try_cloudflare_ai(prompt: str, w: int, h: int, seed: int,
                      cfg: dict, log: Callable) -> Tuple[bytes, str]:
    """调用 Cloudflare Workers AI 图像生成接口。"""
    account_id = cfg.get("cf_account_id", "").strip()
    api_token  = cfg.get("cf_api_token",  "").strip()

    if not account_id or not api_token:
        raise ValueError(
            "需要 Cloudflare Account ID 和 API Token！\n"
            "注册：https://dash.cloudflare.com\n"
            "Token：https://dash.cloudflare.com/profile/api-tokens"
        )

    hq_mode    = bool(cfg.get("variant_hq", False))
    model_list = _CF_HQ_MODELS if hq_mode else _CF_MODELS
    mode_tag   = "HQ变体" if hq_mode else "标准"
    log(f"► Cloudflare Workers AI（免费 10K neurons/天）[{mode_tag}]…")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type":  "application/json",
    }

    def snap(v: int, mx: int) -> int:
        return min(max(256, (v // 64) * 64), mx)

    for model_path, steps, guidance, max_sz in model_list:
        sw = snap(w, max_sz)
        sh = snap(h, max_sz)
        model_short = model_path.split("/")[-1]
        log(f"  模型: {model_short}  {sw}×{sh}  steps={steps}")

        url     = _API_BASE.format(account_id=account_id, model=model_path)
        payload = {
            "prompt": prompt,
            "width":  sw,
            "height": sh,
            "num_steps": steps,
            "seed":   seed % 2_147_483_647,
        }
        if guidance > 0:
            payload["guidance"] = guidance

        try:
            resp = _session.post(url, headers=headers, json=payload,
                                 timeout=_TIMEOUT)
        except requests.exceptions.ConnectionError as e:
            log(f"    网络错误: {e}，换模型…")
            continue
        except requests.exceptions.Timeout:
            log(f"    超时（{_TIMEOUT}s），换模型…")
            continue

        log(f"    状态: {resp.status_code}")

        if resp.status_code == 401:
            raise ValueError("Cloudflare API Token 无效，请检查设置")
        if resp.status_code == 403:
            raise ValueError(
                "Cloudflare Token 权限不足，需要 Workers AI Read 权限\n"
                "请前往 https://dash.cloudflare.com/profile/api-tokens 重新生成"
            )
        if resp.status_code == 429:
            log("    速率限制，等待 5s…")
            time.sleep(5)
            continue
        if resp.status_code in (400, 422):
            try:
                err = resp.json().get("errors", [{"message": _safe_error_text(resp)}])[0].get("message", "")
            except Exception:
                err = _safe_error_text(resp)
            log(f"    参数错误: {err}，换模型…")
            continue
        if resp.status_code != 200:
            log(f"    {resp.status_code}，换模型…")
            continue

        # Cloudflare 响应：{"result": {"image": "<base64>"}, "success": true}
        ct = resp.headers.get("Content-Type", "")

        # 部分模型直接返回图片二进制
        if "image" in ct:
            log(f"  ✓ Cloudflare/{model_short} 成功（直接图片）")
            return resp.content, f"Cloudflare/{model_short}"

        try:
            j = resp.json()
        except Exception:
            log("    无法解析响应，换模型…")
            continue

        if not j.get("success", False):
            errors = j.get("errors", [])
            err_msg = errors[0].get("message", str(errors)) if errors else "未知错误"
            log(f"    API 返回 success=false: {err_msg}，换模型…")
            continue

        result = j.get("result", {})
        img_b64 = result.get("image", "")
        if not img_b64:
            # 有些模型直接把图片放在 result 字节里
            log("    未找到图片数据，换模型…")
            continue

        try:
            img_bytes = base64.b64decode(img_b64)
        except Exception as e:
            log(f"    base64 解码失败: {e}，换模型…")
            continue

        if len(img_bytes) < 1024:
            log("    图片数据过小，换模型…")
            continue

        log(f"  ✓ Cloudflare/{model_short} 成功，{len(img_bytes)//1024}KB")
        return img_bytes, f"Cloudflare/{model_short}"

    raise ValueError(
        "Cloudflare Workers AI 所有模型均失败\n"
        "请检查 Account ID / API Token，或访问 https://dash.cloudflare.com 查看服务状态。"
    )
