"""Audit logger: records all security-relevant operations to both log and database."""

from datetime import datetime
from fastapi import Request
from backend.core.error_handler import logger


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

        try:
            from backend.database_sync import SyncSession
            from backend.models.operational import AuditLog
            with SyncSession() as db:
                log = AuditLog(
                    user_id=user_id,
                    action=f"{request.method} {path}",
                    target_type=path.split("/")[3] if len(path.split("/")) > 3 else "unknown",
                    detail=f"status={response.status_code} ip={client_ip}",
                    ip_address=client_ip,
                    severity=severity.lower(),
                )
                db.add(log)
                db.commit()
        except Exception:
            pass

    return response
