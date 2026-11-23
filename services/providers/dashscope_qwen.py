"""
services/providers/dashscope_qwen.py — 阿里云 DashScope 通义万相 / Qwen-Image
提交: POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis
轮询: GET  https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}
认证: Header Authorization: Bearer <sk-key>
异步任务模式：提交后拿 task_id，轮询 task_status 直到 SUCCEEDED/FAILED

说明：wan2.6-t2i 走新同步协议（multimodal-generation 端点，
input.messages 结构，公共网关 dashscope.aliyuncs.com 纯 API Key 可调，
SDK 默认域名同款）；wan2.5 及以下保持旧异步协议（提交+轮询）。
官方还有 qwen-image-edit（图生图）能力，该端点要求带工作空间 ID 的
专属域名，与本应用"只填一个 Key"的配置模式不匹配，暂不接入。
"""

import threading
import time
from typing import Callable, Tuple

import requests

from config.model_catalog import DASHSCOPE_DEFAULT, DASHSCOPE_MODELS
from services.generation.errors import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderInvalidResponseError,
    ProviderTransientError,
    classify_http_error,
)
from services.providers._net import (
    get_session as _get_session,
    raise_if_cancelled as _raise_if_cancelled,
    safe_error_text as _safe_error_text,
    safe_get_image as _safe_get_image,
)

PROVIDER_INFO = {
    "id": "dashscope_qwen",
    "name": "通义万相 Qwen-Image (阿里云免费额度)",
    "category": "free",
    "config_key": "dashscope_key",
}


_LOCK = threading.Lock()
_LAST_DONE = [0.0]
_MIN_INTV = 2.0

# 旧异步协议端点：wan2.5 及以下；wan2.6 走下方同步端点
# （help.aliyun.com/zh/model-studio/text-to-image-v2-api-reference）。
# wanx2.1 系列已列入阿里云「停止新购及服务下线」公告，已退役。
_SUBMIT_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
# wan2.6 同步端点（公共网关，纯 API Key；与 qwen-vl 系 multimodal 同路径）
_SYNC_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

# wan2.6 尺寸档（总像素 [1280*1280, 1440*1440]，官方推荐五档，"*" 分隔）
_V26_SIZES = [
    "1280*1280",
    "1696*960",
    "960*1696",
    "1472*1104",
    "1104*1472",
]


def _best_size_v26(w: int, h: int) -> str:
    """取与请求宽高比最接近的 wan2.6 官方推荐档。"""

    def score(s: str) -> float:
        sw, sh = (int(v) for v in s.split("*"))
        return abs(sw / sh - max(w / max(h, 1), 1e-6))

    return min(_V26_SIZES, key=score)


_MODEL = DASHSCOPE_DEFAULT
_TIMEOUT = 30
_MAX_POLL = 30
_POLL_INTERVAL = 8


def _norm_model(model: str, log: Callable) -> str:
    """模型选择：本族无向导下拉，cfg["dashscope_model"] 仅能手改——

    目录外值（已退役的 wan2.1 系等）归一化到当前默认并记日志，
    避免拿已下线模型撞「模型不存在」；空值回落目录默认。
    """
    model = (model or "").strip()
    if not model:
        return DASHSCOPE_DEFAULT
    if model not in DASHSCOPE_MODELS:
        log(f"[万相] 模型 {model!r} 不在目录，已归一化到默认 {DASHSCOPE_DEFAULT}")
        model = DASHSCOPE_DEFAULT
    return model


def try_dashscope_qwen(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("dashscope_key", "").strip()
    if not key:
        raise ProviderConfigError("需要阿里云 DashScope API Key！注册：https://dashscope.console.aliyun.com/")

    model = _norm_model(cfg.get("dashscope_model", ""), log)
    if model.startswith("wan2.6"):
        return _generate_sync(model, prompt, w, h, seed, key, log)

    # ── wan2.5 及以下：旧异步协议（提交 + 轮询）──────────────────
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    payload = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {
            "size": f"{w}*{h}",
            "n": 1,
            "seed": seed % 2_147_483_647,
        },
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _get_session().post(_SUBMIT_URL, headers=headers, json=payload, timeout=_TIMEOUT)
        except requests.exceptions.ConnectionError as e:
            _LAST_DONE[0] = time.time()
            raise ProviderTransientError(f"无法连接 DashScope: {e}")
        _LAST_DONE[0] = time.time()

    log(f"► 通义万相  提交任务  状态:{resp.status_code}")
    if resp.status_code == 401:
        raise ProviderAuthError("DashScope API Key 无效")
    if resp.status_code != 200:
        raise classify_http_error(resp.status_code, f"DashScope 提交失败 {resp.status_code}: {_safe_error_text(resp)}")

    task_id = resp.json().get("output", {}).get("task_id", "")
    if not task_id:
        raise ProviderInvalidResponseError(f"DashScope 响应中无 task_id：{resp.json()}")

    log(f"  任务 ID: {task_id}，开始轮询…")
    for i in range(_MAX_POLL):
        _raise_if_cancelled(cfg)
        time.sleep(_POLL_INTERVAL)
        poll_resp = _get_session().get(
            _TASK_URL.format(task_id=task_id),
            headers={"Authorization": f"Bearer {key}"},
            timeout=_TIMEOUT,
        )
        if poll_resp.status_code != 200:
            log(f"    轮询 {i + 1}/{_MAX_POLL} 状态异常 {poll_resp.status_code}，继续等待…")
            continue

        output = poll_resp.json().get("output", {})
        status = output.get("task_status", "")
        log(f"    轮询 {i + 1}/{_MAX_POLL}：{status}")

        if status == "SUCCEEDED":
            results = output.get("results", [])
            if not results or not results[0].get("url"):
                raise ProviderInvalidResponseError(f"DashScope 任务成功但无图片 URL：{output}")
            img_url = results[0]["url"]
            log("  下载图片中…")
            data = _safe_get_image(img_url, timeout=60)
            log(f"  ✓ 通义万相成功  {len(data) // 1024}KB")
            return data, f"DashScope/{model}"

        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            raise ProviderInvalidResponseError(f"DashScope 任务失败：{output.get('message', status)}")
        # PENDING / RUNNING 继续轮询

    raise ProviderTransientError("DashScope 任务轮询超时（240s），请稍后在控制台查看任务状态")


def _generate_sync(model: str, prompt: str, w: int, h: int, seed: int, key: str, log: Callable) -> Tuple[bytes, str]:
    """wan2.6 同步协议：multimodal-generation 端点直接返回图片 URL。

    body 用 input.messages 结构（单轮、仅一个 text）；size 用官方
    推荐档（"*" 分隔，总像素下限 1280*1280）；prompt_extend 关闭——
    官方文档标注其可触发 IPInfringement/DataInspection 误报。
    """
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
        "parameters": {
            "size": _best_size_v26(w, h),
            "n": 1,
            "seed": seed % 2_147_483_647,
            "watermark": False,
            "prompt_extend": False,
        },
    }

    with _LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTV:
            time.sleep(_MIN_INTV - gap)
        try:
            resp = _get_session().post(_SYNC_URL, headers=headers, json=payload, timeout=120)
        except requests.exceptions.ConnectionError as e:
            _LAST_DONE[0] = time.time()
            raise ProviderTransientError(f"无法连接 DashScope: {e}")
        _LAST_DONE[0] = time.time()

    log(f"► 通义万相 2.6  同步生成  状态:{resp.status_code}")
    if resp.status_code == 401:
        raise ProviderAuthError("DashScope API Key 无效")
    if resp.status_code != 200:
        raise classify_http_error(resp.status_code, f"DashScope 生成失败 {resp.status_code}: {_safe_error_text(resp)}")

    # 响应：output.choices[0].message.content[] 内 type=="image" 项带 image URL
    try:
        output = resp.json().get("output", {})
        choices = output.get("choices", [])
        content = choices[0].get("message", {}).get("content", []) if choices else []
        img_url = next((c.get("image") for c in content if c.get("type") == "image" and c.get("image")), "")
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        # 远端 JSON 结构不可信：畸形响应按契约归类为 invalid_response
        raise ProviderInvalidResponseError(f"DashScope 同步响应结构异常：{exc}")
    if not img_url:
        raise ProviderInvalidResponseError(f"DashScope 同步响应中无图片 URL：{resp.json()}")
    data = _safe_get_image(img_url, timeout=60)
    log(f"  ✓ 通义万相 2.6 成功  {len(data) // 1024}KB")
    return data, f"DashScope/{model}"
