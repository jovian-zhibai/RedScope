"""Authentication middleware: protects API routes with JWT verification."""

from fastapi import Request, HTTPException
from jose import jwt, JWTError
from backend.config import get_settings

settings = get_settings()

PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/portal/login",
    "/docs",
    "/openapi.json",
    "/redoc",
}


async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # WebSocket handles its own auth via query param token — skip HTTP middleware
    # but do NOT skip blindly; terminal.py verifies JWT before accepting
    if request.headers.get("upgrade", "").lower() == "websocket":
        return await call_next(request)

    if path in PUBLIC_PATHS or request.method == "OPTIONS":
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录，请先登录")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        request.state.user_id = int(payload.get("sub", 0))
        request.state.username = payload.get("username", "")
        request.state.role = payload.get("role", "viewer")
        request.state.token_type = payload.get("type", "user")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token无效或已过期，请重新登录")

    return await call_next(request)
