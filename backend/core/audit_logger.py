"""Audit logger: records all security-relevant operations to both log and database."""

import asyncio
from datetime import datetime
from fastapi import Request
from backend.core.error_handler import logger


def _write_audit_log(user_id, action, target_type, detail, ip_address, severity):
    try:
        from backend.database_sync import SyncSession
        from backend.models.operational import AuditLog
        with SyncSession() as db:
            log = AuditLog(
                user_id=user_id,
                action=action,
                target_type=target_type,
                detail=detail,
                ip_address=ip_address,
                severity=severity,
            )
            db.add(log)
            db.commit()
    except Exception:
        pass


async def audit_log_middleware(request: Request, call_next):
    response = await call_next(request)

    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None
        username = getattr(request.state, "username", "anonymous") if hasattr(request, "state") else "anonymous"
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        severity = "INFO"
        if any(kw in path for kw in ["/scans", "/emergency-stop", "/run-pipeline"]):
            severity = "HIGH"
        if any(kw in path for kw in ["/credentials", "/hosts", "/terminal", "/proxy"]):
            severity = "HIGH"
        if any(kw in path for kw in ["/tenants", "/accounts", "/transition"]):
            severity = "CRITICAL"

        logger.info(
            f"[AUDIT][{severity}] {request.method} {path} "
            f"user={username}(id={user_id}) ip={client_ip} "
            f"status={response.status_code}"
        )

        loop = asyncio.get_event_loop()
        target_type = path.split("/")[3] if len(path.split("/")) > 3 else "unknown"
        detail = f"status={response.status_code} ip={client_ip}"
        loop.run_in_executor(None, _write_audit_log, user_id, f"{request.method} {path}", target_type, detail, client_ip, severity.lower())

    return response
