"""Rate limiter: prevents brute-force and resource exhaustion. Uses Redis for multi-instance support."""

import time
from collections import defaultdict
from fastapi import Request, HTTPException


class RateLimiter:
    def __init__(self):
        self._redis = None
        self._fallback: dict[str, list[float]] = defaultdict(list)

    def _get_redis(self):
        if self._redis is None:
            try:
                import redis as redis_lib
                from backend.config import get_settings
                self._redis = redis_lib.from_url(get_settings().redis_url)
                self._redis.ping()
            except Exception:
                self._redis = False
        return self._redis if self._redis else None

    def check(self, key: str, max_requests: int, window_seconds: int):
        r = self._get_redis()
        if r:
            self._check_redis(r, key, max_requests, window_seconds)
        else:
            self._check_memory(key, max_requests, window_seconds)

    def _check_redis(self, r, key: str, max_requests: int, window_seconds: int):
        redis_key = f"rl:{key}"
        now = time.time()
        pipe = r.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {str(now): now})
        pipe.expire(redis_key, window_seconds)
        results = pipe.execute()
        count = results[1]
        if count >= max_requests:
            raise HTTPException(429, detail=f"请求过于频繁，请 {window_seconds} 秒后再试")

    def _check_memory(self, key: str, max_requests: int, window_seconds: int):
        now = time.time()
        window_start = now - window_seconds
        self._fallback[key] = [t for t in self._fallback[key] if t > window_start]
        if len(self._fallback[key]) >= max_requests:
            raise HTTPException(429, detail=f"请求过于频繁，请 {window_seconds} 秒后再试")
        self._fallback[key].append(now)


limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    client_ip = request.client.host if request.client else "unknown"

    if path in ("/api/auth/login", "/api/auth/register", "/api/portal/login",
                 "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/portal/login"):
        limiter.check(f"auth:{client_ip}", max_requests=5, window_seconds=60)

    if path.endswith("/scans") and request.method == "POST":
        limiter.check(f"scan:{client_ip}", max_requests=20, window_seconds=60)

    limiter.check(f"api:{client_ip}", max_requests=200, window_seconds=60)

    return await call_next(request)
