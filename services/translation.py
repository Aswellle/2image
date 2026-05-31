"""
services/translation.py — 中英翻译服务
"""
import re
import threading
import time
from typing import Callable, Optional
import requests

# \u6279\u91cf\u751f\u6210\u65f6\u591a\u7ebf\u7a0b\u5e76\u53d1\u8c03\u7528\u4f1a\u6253\u7206 MyMemory \u514d\u8d39\u9650\u901f\uff0c\u52a0\u4e32\u884c\u9501\u4fdd\u62a4
_TRANS_LOCK   = threading.Lock()
_LAST_DONE    = [0.0]
_MIN_INTERVAL = 1.5   # MyMemory \u514d\u8d39\u5c42\u5efa\u8bae\u95f4\u9694


def has_chinese(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def translate_zh_to_en(text: str, log_cb: Optional[Callable[[str], None]] = None) -> str:
    MAX_PROMPT_CHARS = 2000
    if len(text) > MAX_PROMPT_CHARS:
        text = text[:MAX_PROMPT_CHARS]
        if log_cb:
            log_cb(f"提示词过长，已截断至 {MAX_PROMPT_CHARS} 字符")
    with _TRANS_LOCK:
        gap = time.time() - _LAST_DONE[0]
        if gap < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - gap)
        try:
            resp = requests.get(
                "https://api.mymemory.translated.net/get",
                params={"q": text, "langpair": "zh|en"}, timeout=15)
            translated = resp.json().get("responseData", {}).get("translatedText", "")
            if translated and "PLEASE SELECT" not in translated.upper() and len(translated) > 2:
                if log_cb: log_cb(f"翻译成功: {translated}")
                return translated
        except Exception as e:
            if log_cb: log_cb(f"翻译失败（使用原文）: {e}")
        finally:
            _LAST_DONE[0] = time.time()
    return text
