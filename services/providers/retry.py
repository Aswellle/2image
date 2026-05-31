"""
services/providers/retry.py — 通用 Provider 重试 + 限速装饰器
"""
import threading
import time
from functools import wraps
from typing import Callable


def with_retries(
    max_retries: int = 3,
    base_delay: float = 3.0,
    rate_limit_wait: float = 30.0,
    min_interval: float = 2.0,
):
    """
    为 Provider 函数提供统一的重试、指数退避、429 限流处理。

    用法:
        _LOCK = threading.Lock()
        _LAST_DONE = [0.0]

        @with_retries(max_retries=3, min_interval=2.0)
        def try_my_provider(prompt, w, h, seed, cfg, log):
            ...
    """
    lock = threading.Lock()
    last_done = [0.0]

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 限速等待
            with lock:
                gap = time.time() - last_done[0]
                if gap < min_interval:
                    time.sleep(min_interval - gap)

            log = kwargs.get("log") or (args[5] if len(args) > 5 else print)
            last_err = None

            for attempt in range(1, max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    with lock:
                        last_done[0] = time.time()
                    return result
                except ValueError:
                    raise  # 配置错误，不重试
                except Exception as e:
                    last_err = e
                    err_str = str(e)
                    if "429" in err_str or "rate limit" in err_str.lower():
                        log(f"[Retry] 触发速率限制，等待 {rate_limit_wait}s…")
                        time.sleep(rate_limit_wait)
                        continue
                    log(f"[Retry] 尝试 {attempt}/{max_retries} 失败: {e}")
                    if attempt < max_retries:
                        time.sleep(base_delay * attempt)

            with lock:
                last_done[0] = time.time()
            raise RuntimeError(f"全部 {max_retries} 次重试失败: {last_err}")

        return wrapper
    return decorator
