"""Proxy health checker: periodically tests proxy node connectivity."""

import socket
import logging
from datetime import datetime
from sqlalchemy import select
from backend.tasks.celery_app import celery_app
from backend.database_sync import SyncSession
from backend.models.operational import ProxyNode

logger = logging.getLogger("proxy_health")


def _test_socks_proxy(host: str, port: int, timeout: int = 5) -> tuple[bool, int]:
    """Test SOCKS proxy connectivity via TCP handshake.
    
    NOTE: This only verifies TCP reachability, not SOCKS protocol handshake.
    For full SOCKS validation, use a SOCKS client library (e.g., PySocks).
    """
    start = datetime.now()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        latency = int((datetime.now() - start).total_seconds() * 1000)
        return True, latency
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        logger.debug(f"Proxy {host}:{port} unreachable: {e}")
        return False, 0


@celery_app.task(name="check_proxy_health")
def check_proxy_health(project_id: int | None = None):
    with SyncSession() as db:
        query = select(ProxyNode)
        if project_id:
            query = query.where(ProxyNode.project_id == project_id)

        nodes = db.execute(query).scalars().all()
        results = []

        for node in nodes:
            success, latency = _test_socks_proxy(node.host, node.port)

            if success:
                if latency < 500:
                    node.status = "online"
                else:
                    node.status = "unstable"
                node.latency_ms = latency
            else:
                node.status = "offline"
                node.latency_ms = None

            node.last_check_at = datetime.now()
            results.append({
                "node": node.name,
                "status": node.status,
                "latency_ms": node.latency_ms,
            })

        db.commit()

    return {"checked": len(results), "results": results}


@celery_app.task(name="check_all_proxies")
def check_all_proxies():
    return check_proxy_health(project_id=None)
