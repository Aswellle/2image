"""services/providers/openai_dalle.py — OpenAI DALL-E 3"""
import base64
from services.providers._net import SESSION as _session, safe_error_text as _safe_error_text

PROVIDER_INFO = {
    "name": "💎 OpenAI DALL-E 3",
    "category": "paid",
    "config_key": "openai_key",
}



_SIZES = {(1024,1024):"1024x1024", (1792,1024):"1792x1024", (1024,1792):"1024x1792"}

def try_openai_dalle(prompt, w, h, seed, cfg, log):
    key = cfg.get("openai_key","").strip()
    if not key: raise ValueError("需要 OpenAI API Key，请在「💎 付费接口配置」中填写")
    model   = cfg.get("dalle_model",   "dall-e-3")
    quality = cfg.get("dalle_quality", "standard")
    best = min(_SIZES.keys(), key=lambda s: abs(s[0]-w)+abs(s[1]-h))
    size_str = _SIZES[best]
    log(f"► OpenAI DALL-E 3  质量={quality}  尺寸={size_str}")
    resp = _session.post("https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "prompt": prompt, "n": 1, "size": size_str,
              "quality": quality, "response_format": "b64_json"}, timeout=120)
    log(f"  状态: {resp.status_code}")
    if resp.status_code == 401: raise ValueError("OpenAI API Key 无效或已过期")
    if resp.status_code == 402: raise ValueError("OpenAI 账户余额不足")
    if resp.status_code == 429: raise ValueError("OpenAI 速率限制")
    if resp.status_code == 400:
        raise ValueError(f"DALL-E 请求错误: {resp.json().get('error',{}).get('message','')}")
    if resp.status_code != 200: raise ValueError(f"OpenAI 返回 {resp.status_code}: {_safe_error_text(resp)}")
    j = resp.json()
    b64 = j["data"][0].get("b64_json","")
    if not b64: raise ValueError("DALL-E 返回数据中无图片")
    revised = j["data"][0].get("revised_prompt","")
    if revised: log(f"  修订提示词: {revised[:80]}…")
    log(f"  ✓ DALL-E 3 成功 ({quality})")
    return base64.b64decode(b64), f"OpenAI/DALL-E3-{quality}"
