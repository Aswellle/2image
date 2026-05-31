"""
services/providers/_net.py — 共享 HTTP 工具
──────────────────────────────────────────
集中管理所有 provider 共用的网络原语，避免跨 17 个文件的重复代码。

提供：
  SESSION              — 带连接池的共享 requests.Session
  validate_image_url() — 基于 DNS 解析的 SSRF 防护（替代各文件的 _validate_image_url）
  safe_error_text()    — 从 API 响应中提取安全错误文本
"""
import ipaddress
import socket
from contextlib import contextmanager
from urllib.parse import urlparse

import requests

# ── 共享 Session（连接池 + HTTP keep-alive）─────────────────────────
SESSION = requests.Session()
_adapter = requests.adapters.HTTPAdapter(
    pool_connections=2, pool_maxsize=4, max_retries=1)
SESSION.mount("https://", _adapter)
SESSION.mount("http://", _adapter)


def validate_image_url(url: str) -> bool:
    """
    SSRF 防护：验证图片 URL 是否安全可下载。

    修复原 _validate_image_url 的逻辑漏洞：
    - 原版对 DNS 主机名调用 ipaddress.ip_address() 会抛 ValueError，
      被 except 吞掉后直接 return True，导致所有 DNS 名称（含内网域名）均通过。
    - 新版先通过 getaddrinfo 解析主机名，对每个解析结果进行 IP 范围检查，
      解析失败则拒绝（fail-closed）。

    拦截场景：
    - http:// / ftp:// 等非 HTTPS URL
    - 127.0.0.1、::1 等 loopback
    - 10.x、172.16-31.x、192.168.x 等私有 IP
    - 169.254.x.x 链路本地（含云元数据端点）
    - metadata.google.internal 等可解析到内网的 DNS 名称
    - IPv4-mapped IPv6（::ffff:169.254.169.254）
    - 无法解析的主机名（fail-closed）
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return False
        host = parsed.hostname
        port = parsed.port or 443
        try:
            infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror:
            return False  # 无法解析 → 拒绝
        for *_, sockaddr in infos:
            ip = ipaddress.ip_address(sockaddr[0])
            # 处理 IPv4-mapped IPv6（::ffff:169.254.x.x）
            if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                ip = ip.ipv4_mapped
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return False
    except Exception:
        return False  # 任何解析异常都拒绝（fail-closed）
    return True


def safe_error_text(resp) -> str:
    """从 API 响应中提取安全错误文本，避免泄露原始响应体。"""
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
