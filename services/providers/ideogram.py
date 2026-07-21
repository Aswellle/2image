"""
services/providers/ideogram.py — Ideogram v3
文字入图首选接口，可靠渲染 Banner、海报、标签、LOGO 中的文字。
API: POST https://api.ideogram.ai/v1/ideogram-v3/generate
Key: Header  Api-Key: <key>
Body: multipart/form-data（v3 与 v1/v2 的 JSON body 不同）

FIX 2026-07: 旧版端点 POST https://api.ideogram.ai/generate + "model": "V_2"
在当前官方文档中已找不到任何踪迹（v1/v2 完全被 v3 取代），迁移到
v1/ideogram-v3/generate，改用 multipart/form-data，参数名和取值也
不同：aspect_ratio 从 "ASPECT_16_9" 这类写法变成 "16x9"，新增
rendering_speed（FLASH/TURBO/DEFAULT/QUALITY）控制速度与质量的取舍。
"""
import threading
import time
import requests
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "id": "ideogram",
    "name": "Ideogram v3 (文字入图)",
    "category": "commercial",
    "config_key": "ideogram_key",
}


_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0   # Ideogram 免费层建议间隔

_ENDPOINT = "https://api.ideogram.ai/v1/ideogram-v3/generate"

# v3 aspect_ratio 枚举值（官方 API 参考：generate-v3），格式为 "宽x高"
_ASPECTS = [
    (1/3,   "1x3"), (3,     "3x1"),
    (1/2,   "1x2"), (2,     "2x1"),
    (9/16,  "9x16"), (16/9,  "16x9"),
    (10/16, "10x16"), (16/10, "16x10"),
    (2/3,   "2x3"), (3/2,   "3x2"),
    (3/4,   "3x4"), (4/3,   "4x3"),
    (4/5,   "4x5"), (5/4,   "5x4"),
    (1,     "1x1"),
]


def _best_aspect(w: int, h: int) -> str:
    r = w / max(h, 1)
    return min(_ASPECTS, key=lambda x: abs(x[0] - r))[1]


def try_ideogram(prompt: str, w: int, h: int, seed: int,
                 cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("ideogram_key", "").strip()
    if not key:
        raise ValueError("需要 Ideogram API Key！注册：https://ideogram.ai/")

    aspect = _best_aspect(w, h)
    rendering_speed = cfg.get("ideogram_rendering_speed", "DEFAULT")
    log(f"► Ideogram v3  宽高比={aspect}  速度={rendering_speed}")

    # v3 使用 multipart/form-data，而非 v1/v2 的嵌套 JSON body
    files = {
        "prompt":          (None, prompt),
        "aspect_ratio":    (None, aspect),
        "rendering_speed": (None, rendering_speed),
        "seed":            (None, str(seed % 2_147_483_647)),
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _session.post(
                _ENDPOINT,
                headers={"Api-Key": key},
                files=files,
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
    item = data[0]
    if not item.get("is_image_safe", True):
        raise ValueError("Ideogram 安全过滤：该提示词未通过审核，无图片返回")
    img_url = item.get("url", "")
    if not img_url:
        raise ValueError("Ideogram 响应中无图片 URL")

    log("  下载图片中…")
    data = _safe_get_image(img_url, timeout=60)
    log(f"  ✓ Ideogram v3 成功  {len(data) // 1024}KB")
    return data, "Ideogram/v3"
