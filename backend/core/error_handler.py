"""Global error handler and structured logging."""

import logging
import sys
import traceback
from datetime import datetime
from fastapi import Request
from fastapi.responses import JSONResponse

# ─── Structured Logger ────────────────────────────────────

def setup_logging():
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger("redscope")
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.handlers = [handler]

    return root


logger = setup_logging()


# ─── Global Exception Handler ────────────────────────────

async def global_exception_handler(request: Request, exc: Exception):
    error_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]

    logger.error(
        f"[{error_id}] {request.method} {request.url.path} → {type(exc).__name__}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "服务器内部错误",
            "error_id": error_id,
            "message": "请联系管理员并提供错误ID",
        },
    )


# ─── Request Logging Middleware ───────────────────────────

async def request_logging_middleware(request: Request, call_next):
    start = datetime.now()
    response = await call_next(request)
    duration = (datetime.now() - start).total_seconds()

    if duration > 5.0:
        logger.warning(f"慢请求: {request.method} {request.url.path} 耗时 {duration:.2f}s")

    return response
