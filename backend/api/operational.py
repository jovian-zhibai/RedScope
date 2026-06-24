"""Proxy/tunnel management, credential management, compromised hosts,
attack timeline, cleanup, and loot APIs — all operational modules."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.operational import (
    ProxyNode, Credential, CompromisedHost,
    AttackTimeline, CleanupItem, Loot,
)

router = APIRouter()


# ─── Proxy Nodes ───────────────────────────────────────────

class ProxyNodeCreate(BaseModel):
    name: str
    proxy_type: str  # socks5 / socks4 / http / ssh_tunnel
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    upstream_node_id: int | None = None
    reachable_cidrs: list[str]
    tunnel_tool: str | None = None
    tunnel_note: str | None = None


@router.get("/proxy")
async def list_proxies(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProxyNode).where(ProxyNode.project_id == project_id))
    nodes = result.scalars().all()
    return {"items": [
        {
            "id": n.id, "name": n.name, "proxy_type": n.proxy_type,
            "host": n.host, "port": n.port, "status": n.status,
            "latency_ms": n.latency_ms, "reachable_cidrs": n.reachable_cidrs,
            "upstream_node_id": n.upstream_node_id, "tunnel_tool": n.tunnel_tool,
            "tunnel_note": n.tunnel_note,
        } for n in nodes
    ]}


@router.post("/proxy")
async def create_proxy(project_id: int, req: ProxyNodeCreate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.utils.crypto import encrypt_value
    node = ProxyNode(project_id=project_id, **req.model_dump(exclude={"password"}))
    if req.password:
        node.password_enc = encrypt_value(req.password)
    db.add(node)
    await db.flush()
    return {"id": node.id, "name": node.name}


@router.delete("/proxy/{node_id}")
async def delete_proxy(project_id: int, node_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    node = await db.get(ProxyNode, node_id)
    if not node or node.project_id != project_id:
        raise HTTPException(404, "代理节点不存在")
    await db.delete(node)
    await db.flush()
    return {"status": "deleted"}


@router.get("/proxy/tunnel-helper")
async def tunnel_helper(tool: str = "frp", vps_ip: str = "1.2.3.4", vps_port: int = 7000, socks_port: int = 1080):
    commands = {
        "frp": {
            "server": f'./frps -c frps.toml\n\n# frps.toml\nbindPort = {vps_port}',
            "client": f'./frpc -c frpc.toml\n\n# frpc.toml\nserverAddr = "{vps_ip}"\nserverPort = {vps_port}\n\n[[proxies]]\nname = "socks5"\ntype = "tcp"\nremotePort = {socks_port}\n[proxies.plugin]\ntype = "socks5"',
        },
        "chisel": {
            "server": f"./chisel server -p {vps_port} --reverse",
            "client": f"./chisel client {vps_ip}:{vps_port} R:socks",
        },
        "ssh": {
            "server": "# SSH服务端无需额外配置",
            "client": f"ssh -D {socks_port} -N -f user@{vps_ip}",
        },
        "suo5": {
            "server": f"# 上传suo5.jsp到目标Web目录",
            "client": f"./suo5 -d -l 0.0.0.0:{socks_port} -t http://target/suo5.jsp",
        },
    }
    return commands.get(tool, {"error": "不支持的隧道工具"})


# ─── Credentials ───────────────────────────────────────────

class CredentialCreate(BaseModel):
    cred_type: str  # password / hash_ntlm / hash_sha / ssh_key / cookie / token
    username: str | None = None
    secret: str
    domain: str | None = None
    source: str | None = None
    source_host: str | None = None
    related_asset_id: int | None = None


@router.get("/credentials")
async def list_credentials(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Credential).where(Credential.project_id == project_id))
    creds = result.scalars().all()
    return {"items": [
        {
            "id": c.id, "cred_type": c.cred_type, "username": c.username,
            "secret_masked": "****",
            "domain": c.domain, "source": c.source, "source_host": c.source_host,
            "is_cracked": c.is_cracked, "reuse_count": c.reuse_count,
            "reuse_hosts": c.reuse_hosts,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        } for c in creds
    ]}


@router.post("/credentials")
async def create_credential(project_id: int, req: CredentialCreate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.utils.crypto import encrypt_value
    cred = Credential(
        project_id=project_id,
        cred_type=req.cred_type,
        username=req.username,
        secret_enc=encrypt_value(req.secret),
        domain=req.domain,
        source=req.source,
        source_host=req.source_host,
        related_asset_id=req.related_asset_id,
    )
    db.add(cred)
    await db.flush()
    return {"id": cred.id}


@router.post("/credentials/{cred_id}/check-reuse")
async def check_credential_reuse(project_id: int, cred_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    # TODO: actually test credential against assets
    return {"status": "not_implemented", "message": "密码复用检测功能待集成"}


# ─── Compromised Hosts ────────────────────────────────────

class CompromisedHostCreate(BaseModel):
    ip: str
    hostname: str | None = None
    access_level: str  # user / admin / root / system / domain_admin
    shell_type: str | None = None
    persistence: str | None = None
    entry_method: str | None = None
    entry_finding_id: int | None = None
    asset_id: int | None = None


@router.get("/hosts")
async def list_compromised_hosts(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CompromisedHost).where(CompromisedHost.project_id == project_id)
        .order_by(CompromisedHost.compromised_at.desc())
    )
    hosts = result.scalars().all()
    return {"items": [
        {
            "id": h.id, "ip": h.ip, "hostname": h.hostname,
            "access_level": h.access_level, "shell_type": h.shell_type,
            "persistence": h.persistence, "status": h.status,
            "uploaded_files": h.uploaded_files or [],
            "entry_method": h.entry_method, "attck_techniques": h.attck_techniques,
            "compromised_at": h.compromised_at.isoformat() if h.compromised_at else None,
        } for h in hosts
    ]}


@router.post("/hosts")
async def create_compromised_host(project_id: int, req: CompromisedHostCreate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    host = CompromisedHost(project_id=project_id, **req.model_dump())
    db.add(host)
    await db.flush()

    _auto_timeline(db, project_id, f"获取 {req.ip} 的 {req.access_level} 权限", req.ip, "initial_access")
    _auto_cleanup(db, project_id, host.id)
    await db.flush()
    return {"id": host.id}


@router.post("/hosts/{host_id}/upload-file")
async def record_uploaded_file(project_id: int, host_id: int, req: dict, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    host = await db.get(CompromisedHost, host_id)
    if not host or host.project_id != project_id:
        raise HTTPException(404, "主机不存在")

    files = host.uploaded_files or []
    files.append({"path": req.get("path"), "description": req.get("description", ""), "uploaded_at": str(__import__("datetime").datetime.now())})
    host.uploaded_files = files

    cleanup = CleanupItem(
        project_id=project_id, host_id=host_id,
        item_type="uploaded_file",
        description=f"删除文件: {req.get('path')}",
        file_path=req.get("path"),
    )
    db.add(cleanup)
    await db.flush()
    return {"status": "recorded"}


# ─── Attack Timeline ──────────────────────────────────────

class TimelineCreate(BaseModel):
    phase: str
    action: str
    target_host: str | None = None
    result: str = "success"
    attck_id: str | None = None


@router.get("/timeline")
async def get_timeline(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AttackTimeline).where(AttackTimeline.project_id == project_id)
        .order_by(AttackTimeline.timestamp)
    )
    items = result.scalars().all()
    return {"items": [
        {
            "id": t.id, "timestamp": t.timestamp.isoformat() if t.timestamp else None,
            "phase": t.phase, "action": t.action, "target_host": t.target_host,
            "result": t.result, "attck_id": t.attck_id,
            "auto_generated": t.auto_generated,
        } for t in items
    ]}


@router.post("/timeline")
async def add_timeline_entry(project_id: int, req: TimelineCreate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    attck_id = req.attck_id
    if not attck_id:
        from backend.core.attck_mapping import auto_detect_technique
        tid, _ = auto_detect_technique(req.action)
        attck_id = tid or None

    entry = AttackTimeline(
        project_id=project_id,
        timestamp=datetime.now(),
        phase=req.phase, action=req.action,
        target_host=req.target_host,
        result=req.result, attck_id=attck_id,
        auto_generated=False,
    )
    db.add(entry)
    await db.flush()
    return {"id": entry.id, "attck_id": attck_id}


# ─── Cleanup ──────────────────────────────────────────────

@router.get("/cleanup")
async def list_cleanup_items(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CleanupItem).where(CleanupItem.project_id == project_id)
    )
    items = result.scalars().all()
    total = len(items)
    cleaned = sum(1 for i in items if i.is_cleaned)
    return {
        "items": [
            {
                "id": i.id, "item_type": i.item_type, "description": i.description,
                "file_path": i.file_path, "is_cleaned": i.is_cleaned,
                "cleaned_at": i.cleaned_at.isoformat() if i.cleaned_at else None,
            } for i in items
        ],
        "total": total, "cleaned": cleaned,
        "progress": round(cleaned / total * 100) if total > 0 else 0,
    }


@router.put("/cleanup/{item_id}/mark")
async def mark_cleaned(project_id: int, item_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    item = await db.get(CleanupItem, item_id)
    if not item or item.project_id != project_id:
        raise HTTPException(404, "清理项不存在")
    item.is_cleaned = True
    item.cleaned_at = datetime.now()
    await db.flush()
    return {"status": "marked"}


# ─── Loot ─────────────────────────────────────────────────

class LootCreate(BaseModel):
    loot_type: str
    title: str
    description: str | None = None
    impact: str = "medium"
    host_id: int | None = None


@router.get("/loots")
async def list_loots(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Loot).where(Loot.project_id == project_id))
    items = result.scalars().all()
    return {"items": [
        {"id": l.id, "loot_type": l.loot_type, "title": l.title,
         "description": l.description, "impact": l.impact,
         "created_at": l.created_at.isoformat() if l.created_at else None}
        for l in items
    ]}


@router.post("/loots")
async def create_loot(project_id: int, req: LootCreate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    loot = Loot(project_id=project_id, **req.model_dump())
    db.add(loot)
    await db.flush()
    return {"id": loot.id}


# ─── Helpers ──────────────────────────────────────────────

def _auto_timeline(db, project_id, action, target_host, phase):
    from datetime import datetime
    entry = AttackTimeline(
        project_id=project_id, timestamp=datetime.now(),
        phase=phase, action=action, target_host=target_host,
        result="success", auto_generated=True,
    )
    db.add(entry)


def _auto_cleanup(db, project_id, host_id):
    defaults = [
        ("shell", "断开所有Shell连接"),
        ("tunnel", "关闭隧道/代理"),
        ("log", "清除操作日志和历史记录"),
    ]
    for item_type, desc in defaults:
        db.add(CleanupItem(project_id=project_id, host_id=host_id, item_type=item_type, description=desc))
