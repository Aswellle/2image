"""
services/providers/dashscope_qwen.py — 阿里云 DashScope 通义万相 / Qwen-Image
提交: POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis
轮询: GET  https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}
认证: Header Authorization: Bearer <sk-key>
异步任务模式：提交后拿 task_id，轮询 task_status 直到 SUCCEEDED/FAILED

说明：官方还有 qwen-image-edit（图生图）能力，但那个端点要求
{WorkspaceId}.cn-beijing.maas.aliyuncs.com 这种带工作空间 ID 的
专属域名（不是纯 API Key 就能调），与本应用"只填一个 Key"的
配置模式不匹配，这里暂只做文生图；如需图生图请自行在 config.json
里补充 workspace 相关参数后扩展本文件。
"""
import threading
import time
import requests
from typing import Callable, Tuple
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text, safe_get_image as _safe_get_image

PROVIDER_INFO = {
    "id": "dashscope_qwen",
    "name": "通义万相 Qwen-Image (阿里云免费额度)",
    "category": "free",
    "config_key": "dashscope_key",
}


_LOCK      = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV  = 2.0

_SUBMIT_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
_TASK_URL   = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
_MODEL      = "wanx2.1-t2i-turbo"
_TIMEOUT    = 30
_MAX_POLL   = 30
_POLL_INTERVAL = 8


def try_dashscope_qwen(
    prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable
) -> Tuple[bytes, str]:
    key = cfg.get("dashscope_key", "").strip()
    if not key:
        raise ValueError("需要阿里云 DashScope API Key！注册：https://dashscope.console.aliyun.com/")

    headers = {
        "Authorization":       f"Bearer {key}",
        "Content-Type":        "application/json",
        "X-DashScope-Async":   "enable",
    }
    payload = {
        "model": cfg.get("dashscope_model", _MODEL),
        "input": {"prompt": prompt},
        "parameters": {
            "size": f"{w}*{h}",
            "n":    1,
            "seed": seed % 2_147_483_647,
        },
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _session.post(_SUBMIT_URL, headers=headers, json=payload, timeout=_TIMEOUT)
        except requests.exceptions.ConnectionError as e:
            _LAST_DONE[0] = time.time()
            raise ValueError(f"无法连接 DashScope: {e}")
        _LAST_DONE[0] = time.time()

    log(f"► 通义万相  提交任务  状态:{resp.status_code}")
    if resp.status_code == 401:
        raise ValueError("DashScope API Key 无效")
    if resp.status_code != 200:
        raise ValueError(f"DashScope 提交失败 {resp.status_code}: {_safe_error_text(resp)}")

    task_id = resp.json().get("output", {}).get("task_id", "")
    if not task_id:
        raise ValueError(f"DashScope 响应中无 task_id：{resp.json()}")

    log(f"  任务 ID: {task_id}，开始轮询…")
    for i in range(_MAX_POLL):
        time.sleep(_POLL_INTERVAL)
        poll_resp = _session.get(
            _TASK_URL.format(task_id=task_id),
            headers={"Authorization": f"Bearer {key}"},
            timeout=_TIMEOUT,
        )
        if poll_resp.status_code != 200:
            log(f"    轮询 {i+1}/{_MAX_POLL} 状态异常 {poll_resp.status_code}，继续等待…")
            continue

        output = poll_resp.json().get("output", {})
        status = output.get("task_status", "")
        log(f"    轮询 {i+1}/{_MAX_POLL}：{status}")

        if status == "SUCCEEDED":
            results = output.get("results", [])
            if not results or not results[0].get("url"):
                raise ValueError(f"DashScope 任务成功但无图片 URL：{output}")
            img_url = results[0]["url"]
            log("  下载图片中…")
            data = _safe_get_image(img_url, timeout=60)
            log(f"  ✓ 通义万相成功  {len(data)//1024}KB")
            return data, "DashScope/Qwen-Image"

        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            raise ValueError(f"DashScope 任务失败：{output.get('message', status)}")
        # PENDING / RUNNING 继续轮询

    raise ValueError("DashScope 任务轮询超时（240s），请稍后在控制台查看任务状态")
