"""
services/providers/ideogram.py — Ideogram v4
文字入图首选接口，可靠渲染 Banner、海报、标签、LOGO 中的文字。
API: POST https://api.ideogram.ai/v1/ideogram-v4/generate
Key: Header  Api-Key: <key>
Body: multipart/form-data（v4 与 v1/v2 的 JSON body 不同）

UPDATE 2026-08: Ideogram 4.0 于 2026-06-03 发布，官方当前生成端点改为
v1/ideogram-v4/generate，模型 ID 为 V_4。v4 的 aspect_ratio 用冒号格式
（"16:9" 而非 v3 的 "16x9"），并支持更高分辨率（每边 256–2048，宽高比至 6:1）。
v3 端点仍可用，但已非当前代际，这里迁移到 v4。
"""
import threading
import time
import requests
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "id": "ideogram",
    "name": "Ideogram v4 (文字入图)",
    "category": "commercial",
    "config_key": "ideogram_key",
}


_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0   # Ideogram 免费层建议间隔

_ENDPOINT = "https://api.ideogram.ai/v1/ideogram-v4/generate"
_MODEL    = "V_4"

# v4 aspect_ratio 枚举值（官方 API 参考：generate-v4），格式为 "宽:高"
_ASPECTS = [
    (1/3,   "1:3"), (3,     "3:1"),
    (1/2,   "1:2"), (2,     "2:1"),
    (9/16,  "9:16"), (16/9,  "16:9"),
    (10/16, "10:16"), (16/10, "16:10"),
    (2/3,   "2:3"), (3/2,   "3:2"),
    (3/4,   "3:4"), (4/3,   "4:3"),
    (4/5,   "4:5"), (5/4,   "5:4"),
    (1,     "1:1"),
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
    log(f"► Ideogram v4  宽高比={aspect}  速度={rendering_speed}")

    # v4 使用 multipart/form-data，需显式传 model=V_4
    files = {
        "model":           (None, _MODEL),
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
    log(f"  ✓ Ideogram v4 成功  {len(data) // 1024}KB")
    return data, "Ideogram/v4"
