"""services/providers/stability_ai.py — Stability AI"""
import base64, requests
# Session with connection pooling for HTTP keep-alive
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(
    pool_connections=2, pool_maxsize=4, max_retries=1)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

PROVIDER_INFO = {
    "name": "💎 Stability AI",
    "category": "paid",
    "config_key": "stability_key",
}

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

_ASPECT = {(1024,1024):"1:1",(1344,768):"16:9",(768,1344):"9:16",
           (1216,832):"3:2",(832,1216):"2:3",(1152,896):"4:3",
           (896,1152):"3:4",(1536,640):"21:9"}
_EP = {"core":"https://api.stability.ai/v2beta/stable-image/generate/core",
       "ultra":"https://api.stability.ai/v2beta/stable-image/generate/ultra",
       "sd3.5-large":"https://api.stability.ai/v2beta/stable-image/generate/sd3"}

def _aspect(w,h):
    r = w/max(h,1)
    return _ASPECT[min(_ASPECT.keys(), key=lambda s: abs(s[0]/s[1]-r))]

def try_stability_ai(prompt, w, h, seed, cfg, log):
    key = cfg.get("stability_key","").strip()
    if not key: raise ValueError("需要 Stability AI API Key，请在「💎 付费接口配置」中填写")
    model = cfg.get("stability_model","core"); aspect = _aspect(w,h)
    url = _EP.get(model, _EP["core"])
    log(f"► Stability AI  模型={model}  宽高比={aspect}")
    data = {"prompt":prompt,"aspect_ratio":aspect,"output_format":"png","seed":str(seed%4294967294)}
    if model == "sd3.5-large": data["model"] = "sd3.5-large"
    resp = _session.post(url, headers={"Authorization":f"Bearer {key}","Accept":"image/*"},
                         files={k:(None,v) for k,v in data.items()}, timeout=120)
    log(f"  状态: {resp.status_code}")
    if resp.status_code == 401: raise ValueError("Stability AI Key 无效或已过期")
    if resp.status_code == 402: raise ValueError("Stability AI 余额不足")
    if resp.status_code == 422: raise ValueError(f"Stability AI 参数错误: {_safe_error_text(resp)}")
    if resp.status_code != 200: raise ValueError(f"Stability AI 返回 {resp.status_code}: {_safe_error_text(resp)}")
    if "image" in resp.headers.get("Content-Type",""):
        log(f"  ✓ Stability AI {model} 成功"); return resp.content, f"StabilityAI/{model}"
    try:
        j = resp.json()
        for item in (j.get("artifacts") or j.get("images") or []):
            b64 = item.get("base64") or item.get("image")
            if b64:
                log(f"  ✓ Stability AI {model} 成功（JSON）")
                return base64.b64decode(b64), f"StabilityAI/{model}"
    except Exception: pass
    raise ValueError(f"Stability AI 响应格式未知")
