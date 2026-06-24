"""Rate limiter: prevents brute-force and resource exhaustion."""

import time
from collections import defaultdict
from fastapi import Request, HTTPException


class RateLimiter:
    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: int):
        now = time.time()
        window_start = now - window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        if len(self._requests[key]) >= max_requests:
            raise HTTPException(429, detail=f"请求过于频繁，请 {window_seconds} 秒后再试")
        self._requests[key].append(now)


limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    client_ip = request.client.host if request.client else "unknown"

    # Auth endpoints: strict rate limiting
    if path in ("/api/auth/login", "/api/auth/register", "/api/portal/login"):
        limiter.check(f"auth:{client_ip}", max_requests=10, window_seconds=60)

    # Scan creation: moderate limiting
    if path.endswith("/scans") and request.method == "POST":
        limiter.check(f"scan:{client_ip}", max_requests=20, window_seconds=60)

    # General API: loose limiting
    limiter.check(f"api:{client_ip}", max_requests=200, window_seconds=60)

    return await call_next(request)
