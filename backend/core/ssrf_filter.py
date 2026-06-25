"""SSRF protection: block requests to internal/private network addresses."""

import ipaddress
from urllib.parse import urlparse
import socket
from fastapi import HTTPException


BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"),
]


def validate_url_not_internal(url: str) -> str:
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(400, "无效的 URL")

    try:
        resolved = socket.getaddrinfo(hostname, None)
        for _, _, _, _, addr in resolved:
            ip = ipaddress.ip_address(addr[0])
            for network in BLOCKED_NETWORKS:
                if ip in network:
                    raise HTTPException(400, f"目标地址 {hostname} 解析到内网地址，已拦截 (SSRF 防护)")
    except socket.gaierror:
        pass
    except HTTPException:
        raise
    except Exception:
        pass

    return url
