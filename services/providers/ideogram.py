"""
services/providers/ideogram.py — Ideogram v2
文字入图首选接口，可靠渲染 Banner、海报、标签、LOGO 中的文字。
API: POST https://api.ideogram.ai/generate
Key: Header  Api-Key: <key>
"""
import threading
import time
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, validate_image_url as _validate_image_url, safe_error_text as _safe_error_text

PROVIDER_INFO = {
    "name": "Ideogram v2 (文字入图)",
    "category": "commercial",
    "config_key": "ideogram_key",
}


_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0   # Ideogram 免费层建议间隔

# 宽高比选择表（w/h 比值越接近越优先）
_ASPECTS = [
    ((1024, 1024), "ASPECT_1_1"),
    ((1344,  768), "ASPECT_16_9"),
    (( 768, 1344), "ASPECT_9_16"),
    ((1280,  800), "ASPECT_16_10"),
    (( 800, 1280), "ASPECT_10_16"),
    ((1024,  768), "ASPECT_4_3"),
    (( 768, 1024), "ASPECT_3_4"),
    ((1024,  682), "ASPECT_3_2"),
    (( 682, 1024), "ASPECT_2_3"),
]


def _best_aspect(w: int, h: int) -> str:
    r = w / max(h, 1)
    return min(_ASPECTS, key=lambda x: abs(x[0][0] / x[0][1] - r))[1]


def try_ideogram(prompt: str, w: int, h: int, seed: int,
                 cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("ideogram_key", "").strip()
    if not key:
        raise ValueError("需要 Ideogram API Key！注册：https://ideogram.ai/")

    aspect = _best_aspect(w, h)
    log(f"► Ideogram v2  宽高比={aspect}")

    payload = {
        "image_request": {
            "prompt":              prompt,
            "aspect_ratio":        aspect,
            "model":               "V_2",
            "magic_prompt_option": "OFF",   # 关闭自动改写，保持用户原意
            "seed":                seed % 2_147_483_647,
        }
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _session.post(
                "https://api.ideogram.ai/generate",
                headers={"Api-Key": key, "Content-Type": "application/json"},
                json=payload,
                timeout=120,
            )
        except requests.exceptions.ConnectionError as e:
            _LAST_DONE[0] = time.time()
            raise ValueError(f"无法连接 Ideogram: {e}")
        _LAST_DONE[0] = time.time()

    log(f"  状态: {resp.status_code}")
    if resp.status_code == 401:
        raise ValueError("Ideogram API Key 无效")
    if resp.status_code == 429:
        raise ValueError("Ideogram 速率限制，请稍后再试")
    if resp.status_code == 400:
        raise ValueError(f"Ideogram 请求错误: {_safe_error_text(resp)}")
    if resp.status_code != 200:
        raise ValueError(f"Ideogram 返回 {resp.status_code}: {_safe_error_text(resp)}")

    data = resp.json().get("data", [])
    if not data:
        raise ValueError("Ideogram 返回数据为空")
    img_url = data[0].get("url", "")
    if not img_url:
        raise ValueError("Ideogram 响应中无图片 URL")

    log("  下载图片中…")
    if not _validate_image_url(img_url):
        raise RuntimeError(f"Blocked unsafe image URL: {img_url[:100]}")
    ir = _session.get(img_url, timeout=60)
    ir.raise_for_status()
    log(f"  ✓ Ideogram v2 成功  {len(ir.content) // 1024}KB")
    return ir.content, "Ideogram/v2"
