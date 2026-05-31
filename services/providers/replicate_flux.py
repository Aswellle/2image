"""services/providers/replicate_flux.py — Replicate FLUX"""
import base64, ipaddress, time, requests
# Session with connection pooling for HTTP keep-alive
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(
    pool_connections=2, pool_maxsize=4, max_retries=1)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

from urllib.parse import urlparse

PROVIDER_INFO = {
    "name": "💎 Replicate FLUX",
    "category": "paid",
    "config_key": "replicate_key",
    "try_fn": "try_replicate",
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

_MODELS = {"flux-1.1-pro":"black-forest-labs/flux-1.1-pro",
           "flux-pro":"black-forest-labs/flux-pro",
           "flux-dev":"black-forest-labs/flux-dev"}

def try_replicate(prompt, w, h, seed, cfg, log):
    key = cfg.get("replicate_key","").strip()
    if not key: raise ValueError("需要 Replicate API Token，请在「💎 付费接口配置」中填写")
    slug = cfg.get("replicate_model","flux-1.1-pro")
    path = _MODELS.get(slug, _MODELS["flux-1.1-pro"])
    mw = max(64, min(w,1440)//64*64); mh = max(64, min(h,1440)//64*64)
    log(f"► Replicate  模型={path}  {mw}×{mh}")
    headers = {"Authorization":f"Bearer {key}","Content-Type":"application/json","Prefer":"wait"}
    body = {"input":{"prompt":prompt,"width":mw,"height":mh,"num_outputs":1,"seed":seed%2147483647}}
    if slug=="flux-dev": body["input"].update({"num_inference_steps":28,"guidance_scale":3.5})
    resp = _session.post(f"https://api.replicate.com/v1/models/{path}/predictions",
                         headers=headers, json=body, timeout=90)
    log(f"  状态: {resp.status_code}")
    if resp.status_code == 401: raise ValueError("Replicate Token 无效")
    if resp.status_code == 402: raise ValueError("Replicate 余额不足")
    if resp.status_code not in (200,201): raise ValueError(f"Replicate 返回 {resp.status_code}: {_safe_error_text(resp)}")
    j = resp.json(); pred_id = j.get("id"); status = j.get("status",""); output = j.get("output")
    if status != "succeeded" and pred_id:
        log(f"  轮询中（id={pred_id[:8]}）…")
        for i in range(40):
            time.sleep(3)
            pr = _session.get(f"https://api.replicate.com/v1/predictions/{pred_id}",
                              headers={"Authorization":f"Bearer {key}"}, timeout=20)
            pr.raise_for_status(); pj=pr.json(); status=pj.get("status","")
            log(f"  [{i+1}/40] status={status}")
            if status=="succeeded": output=pj.get("output"); break
            if status in ("failed","canceled"): raise ValueError(f"Replicate 任务失败: {pj.get('error','')}")
        else: raise TimeoutError("Replicate 120s 超时")
    if isinstance(output,list) and output: img_url=output[0]
    elif isinstance(output,str): img_url=output
    else: raise ValueError(f"Replicate 输出格式未知: {output}")
    if img_url.startswith("data:"):
        log(f"  ✓ Replicate {slug} 成功（data URI）")
        return base64.b64decode(img_url.split(",",1)[1]), f"Replicate/{slug}"
    if not _validate_image_url(img_url):
        raise RuntimeError(f"Blocked unsafe image URL: {img_url[:100]}")
    log(f"  下载图片: {img_url[:60]}…")
    ir = _session.get(img_url, timeout=60); ir.raise_for_status()
    log(f"  ✓ Replicate {slug} 成功")
    return ir.content, f"Replicate/{slug}"
