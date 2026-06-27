from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from backend.config import get_settings
from backend.core.auth_middleware import auth_middleware
from backend.core.error_handler import global_exception_handler, request_logging_middleware, logger
from backend.core.rate_limiter import rate_limit_middleware
from backend.core.audit_logger import audit_log_middleware
from backend.database import get_db, init_db
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api import (
    auth, projects, scope, assets, scanning, findings, knowledge, plugins,
    reports, operational, terminal, manual_testing, baseline,
    tenants, client_portal, redblue, workflow, wiring, sessions,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RedScope starting up...")
    await init_db()
    logger.info("Database initialized")
    from backend.core.plugin_manager import plugin_manager
    plugin_manager.load_all()
    logger.info(f"Loaded {len(plugin_manager.list_plugins())} plugins")
    yield
    logger.info("RedScope shutting down...")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="渗透测试一体化工作台",
    lifespan=lifespan,
)

app.add_exception_handler(Exception, global_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BaseHTTPMiddleware, dispatch=audit_log_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=request_logging_middleware)

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
except ImportError:
    pass

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["项目管理"])
app.include_router(scope.router, prefix="/api/v1/projects/{project_id}/scope", tags=["边界管理"])
app.include_router(assets.router, prefix="/api/v1/projects/{project_id}/assets", tags=["资产管理"])
app.include_router(scanning.router, prefix="/api/v1/projects/{project_id}/scans", tags=["扫描任务"])
app.include_router(findings.router, prefix="/api/v1/projects/{project_id}/findings", tags=["漏洞管理"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["漏洞情报"])
app.include_router(plugins.router, prefix="/api/v1/plugins", tags=["插件管理"])
app.include_router(reports.router, prefix="/api/v1/projects/{project_id}/reports", tags=["报告生成"])
app.include_router(operational.router, prefix="/api/v1/projects/{project_id}/ops", tags=["作战管理"])
app.include_router(terminal.router, prefix="/ws", tags=["终端"])
app.include_router(manual_testing.router, prefix="/api/v1/testing", tags=["手工测试"])
app.include_router(baseline.router, prefix="/api/v1/baseline", tags=["基线合规"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["多租户"])
app.include_router(client_portal.router, prefix="/api/v1/portal", tags=["客户门户"])
app.include_router(redblue.router, prefix="/api/v1/projects/{project_id}/redblue", tags=["红蓝对抗"])
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["工单审批"])
app.include_router(wiring.router, prefix="/api/v1", tags=["核心能力"])
app.include_router(sessions.router, prefix="/api/v1", tags=["工作Session"])


@app.get("/api/v1/health")
@app.get("/api/health")
async def health_check():
    from sqlalchemy import text
    from backend.database import async_session
    status = {"app": settings.app_name, "version": settings.app_version}
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        status["database"] = "ok"
    except Exception:
        status["database"] = "error"

    try:
        from redis.asyncio import Redis as AsyncRedis
        r = AsyncRedis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        status["redis"] = "ok"
    except Exception:
        status["redis"] = "error"

    all_ok = status.get("database") == "ok" and status.get("redis") == "ok"
    status["status"] = "ok" if all_ok else "degraded"
    return status


@app.get("/api/v1/dashboard/summary")
async def dashboard_summary(request: Request, db: AsyncSession = Depends(get_db)):
    from backend.models.project import Project
    from backend.models.finding import Finding
    from backend.models.scan_task import ScanTask

    user_id = getattr(request.state, "user_id", 0)
    role = getattr(request.state, "role", "viewer")
    tenant_id = getattr(request.state, "tenant_id", None)

    proj_query = select(Project).order_by(Project.updated_at.desc())
    if role != "admin":
        if tenant_id:
            proj_query = proj_query.where((Project.tenant_id == tenant_id) | (Project.created_by == user_id))
        else:
            proj_query = proj_query.where(Project.created_by == user_id)

    proj_result = await db.execute(proj_query)
    projects = proj_result.scalars().all()
    project_ids = [p.id for p in projects]

    total_findings = 0
    crit_high = 0
    fixed = 0
    if project_ids:
        from sqlalchemy import case
        total_findings = await db.scalar(
            select(func.count()).where(Finding.project_id.in_(project_ids), Finding.deleted_at == None)
        ) or 0
        crit_high = await db.scalar(
            select(func.count()).where(
                Finding.project_id.in_(project_ids),
                Finding.deleted_at == None,
                Finding.severity.in_(["critical", "high"]),
            )
        ) or 0
        fixed = await db.scalar(
            select(func.count()).where(
                Finding.project_id.in_(project_ids),
                Finding.deleted_at == None,
                Finding.fix_status == "fixed",
            )
        ) or 0

    active_scans = []
    if project_ids:
        scan_result = await db.execute(
            select(ScanTask).where(
                ScanTask.project_id.in_(project_ids),
                ScanTask.status.in_(["running", "pending"]),
            )
        )
        active_scans = [
            {"id": s.id, "task_name": s.task_name, "scan_strategy": s.scan_strategy,
             "progress": s.progress, "project_id": s.project_id}
            for s in scan_result.scalars().all()
        ]

    from backend.models.asset import Asset
    # Batch query to avoid N+1: fetch all asset/finding counts in one query
    if project_ids:
        asset_counts_q = (
            select(Asset.project_id, func.count().label("cnt"))
            .where(Asset.project_id.in_(project_ids), Asset.deleted_at == None)
            .group_by(Asset.project_id)
        )
        finding_counts_q = (
            select(Finding.project_id, func.count().label("cnt"))
            .where(Finding.project_id.in_(project_ids), Finding.deleted_at == None)
            .group_by(Finding.project_id)
        )
        asset_counts = {pid: cnt for pid, cnt in (await db.execute(asset_counts_q)).all()}
        finding_counts = {pid: cnt for pid, cnt in (await db.execute(finding_counts_q)).all()}
    else:
        asset_counts = {}
        finding_counts = {}

    projects_data = []
    for p in projects[:10]:
        projects_data.append({
            "id": p.id, "name": p.name, "mode": p.mode, "status": p.status,
            "client_name": p.client_name,
            "asset_count": asset_counts.get(p.id, 0),
            "finding_count": finding_counts.get(p.id, 0),
        })

    recent_findings_data = []
    if project_ids:
        project_name_map = {p.id: p.name for p in projects}
        findings_result = await db.execute(
            select(Finding).where(
                Finding.project_id.in_(project_ids), Finding.deleted_at == None
            ).order_by(Finding.created_at.desc()).limit(10)
        )
        for f in findings_result.scalars().all():
            host = None
            if f.asset_id:
                host = await db.scalar(select(Asset.host).where(Asset.id == f.asset_id))
            recent_findings_data.append({
                "id": f.id, "title": f.title, "severity": f.severity,
                "host": host, "found_by": f.found_by, "project_id": f.project_id,
                "project_name": project_name_map.get(f.project_id, ""),
            })

    return {
        "active_projects": len(projects),
        "total_findings": total_findings,
        "critical_high": crit_high,
        "fix_rate": round(fixed / total_findings * 100) if total_findings > 0 else 0,
        "active_scans": active_scans,
        "recent_projects": projects_data,
        "recent_findings": recent_findings_data,
    }


@app.get("/api/v1/global/scans")
async def global_scans(request: Request, db: AsyncSession = Depends(get_db)):
    from backend.models.project import Project
    from backend.models.scan_task import ScanTask

    user_id = getattr(request.state, "user_id", 0)
    role = getattr(request.state, "role", "viewer")
    tenant_id = getattr(request.state, "tenant_id", None)

    proj_query = select(Project.id, Project.name)
    if role != "admin":
        if tenant_id:
            proj_query = proj_query.where((Project.tenant_id == tenant_id) | (Project.created_by == user_id))
        else:
            proj_query = proj_query.where(Project.created_by == user_id)
    proj_result = await db.execute(proj_query)
    project_map = {pid: name for pid, name in proj_result.all()}

    if not project_map:
        return {"items": []}

    scan_result = await db.execute(
        select(ScanTask)
        .where(ScanTask.project_id.in_(project_map.keys()))
        .order_by(ScanTask.created_at.desc())
        .limit(50)
    )
    tasks = scan_result.scalars().all()

    return {"items": [
        {
            "id": t.id, "task_name": t.task_name, "scan_strategy": t.scan_strategy,
            "engines": t.engines, "status": t.status, "progress": t.progress,
            "total_targets": t.total_targets, "scanned_count": t.scanned_count,
            "vulns_found": t.vulns_found, "project_id": t.project_id,
            "project_name": project_map.get(t.project_id, ""),
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        }
        for t in tasks
    ]}


@app.get("/api/v1/global/findings")
async def global_findings(
    request: Request, severity: str = None, fix_status: str = None,
    db: AsyncSession = Depends(get_db),
):
    from backend.models.project import Project
    from backend.models.finding import Finding

    user_id = getattr(request.state, "user_id", 0)
    role = getattr(request.state, "role", "viewer")
    tenant_id = getattr(request.state, "tenant_id", None)

    proj_query = select(Project.id, Project.name)
    if role != "admin":
        if tenant_id:
            proj_query = proj_query.where((Project.tenant_id == tenant_id) | (Project.created_by == user_id))
        else:
            proj_query = proj_query.where(Project.created_by == user_id)
    proj_result = await db.execute(proj_query)
    project_map = {pid: name for pid, name in proj_result.all()}

    if not project_map:
        return {"items": [], "stats": {}}

    query = select(Finding).where(Finding.project_id.in_(project_map.keys()), Finding.deleted_at == None)
    if severity:
        query = query.where(Finding.severity == severity)
    if fix_status:
        query = query.where(Finding.fix_status == fix_status)
    query = query.order_by(Finding.severity, Finding.created_at.desc()).limit(100)

    result = await db.execute(query)
    findings = result.scalars().all()

    total = await db.scalar(select(func.count()).where(Finding.project_id.in_(project_map.keys()), Finding.deleted_at == None)) or 0
    crit = await db.scalar(select(func.count()).where(Finding.project_id.in_(project_map.keys()), Finding.deleted_at == None, Finding.severity == "critical")) or 0
    high = await db.scalar(select(func.count()).where(Finding.project_id.in_(project_map.keys()), Finding.deleted_at == None, Finding.severity == "high")) or 0

    return {
        "items": [
            {"id": f.id, "title": f.title, "severity": f.severity, "vuln_type": f.vuln_type,
             "fix_status": f.fix_status, "found_by": f.found_by, "project_id": f.project_id,
             "project_name": project_map.get(f.project_id, ""),
             "created_at": f.created_at.isoformat() if f.created_at else None}
            for f in findings
        ],
        "stats": {"total": total, "critical": crit, "high": high},
    }


@app.get("/api/v1/global/assets")
async def global_assets(request: Request, search: str = None, db: AsyncSession = Depends(get_db)):
    from backend.models.project import Project
    from backend.models.asset import Asset

    user_id = getattr(request.state, "user_id", 0)
    role = getattr(request.state, "role", "viewer")
    tenant_id = getattr(request.state, "tenant_id", None)

    proj_query = select(Project.id, Project.name)
    if role != "admin":
        if tenant_id:
            proj_query = proj_query.where((Project.tenant_id == tenant_id) | (Project.created_by == user_id))
        else:
            proj_query = proj_query.where(Project.created_by == user_id)
    proj_result = await db.execute(proj_query)
    project_map = {pid: name for pid, name in proj_result.all()}

    if not project_map:
        return {"items": [], "total": 0}

    query = select(Asset).where(Asset.project_id.in_(project_map.keys()), Asset.deleted_at == None)
    if search:
        escaped_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Asset.host.ilike(f"%{escaped_search}%"))
    query = query.order_by(Asset.first_seen_at.desc()).limit(100)

    result = await db.execute(query)
    assets = result.scalars().all()
    total = await db.scalar(select(func.count()).where(Asset.project_id.in_(project_map.keys()), Asset.deleted_at == None)) or 0

    return {
        "items": [
            {"id": a.id, "host": a.host, "port": a.port, "application": a.application,
             "server": a.server, "importance": a.importance, "is_alive": a.is_alive,
             "project_id": a.project_id, "project_name": project_map.get(a.project_id, "")}
            for a in assets
        ],
        "total": total,
    }


@app.get("/api/v1/search")
@app.get("/api/search")
async def global_search(q: str = "", request: Request = None, db: AsyncSession = Depends(get_db)):
    from backend.models.project import Project
    from backend.models.asset import Asset
    from backend.models.finding import Finding
    from backend.models.vuln_knowledge import VulnKnowledge

    if not q or len(q) < 2:
        return {"projects": [], "assets": [], "findings": [], "knowledge": []}

    # Escape SQL LIKE wildcards to prevent injection
    def _escape_like(s: str) -> str:
        return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    escaped_q = _escape_like(q)
    pattern = f"%{escaped_q}%"
    is_admin = getattr(request.state, 'role', '') == 'admin' if request else False
    user_id = getattr(request.state, 'user_id', 0) if request else 0

    proj_query = select(Project).where(Project.name.ilike(pattern) | Project.client_name.ilike(pattern))
    if not is_admin:
        proj_query = proj_query.where(Project.created_by == user_id)
    proj_result = await db.execute(proj_query.limit(5))
    proj_rows = proj_result.scalars().all()
    project_ids = [p.id for p in proj_rows]
    projects_list = [{"id": p.id, "name": p.name, "type": "project"} for p in proj_rows]

    asset_query = select(Asset).where(Asset.host.ilike(pattern) | Asset.application.ilike(pattern))
    if not is_admin and project_ids:
        asset_query = asset_query.where(Asset.project_id.in_(project_ids))
    elif not is_admin:
        asset_query = asset_query.where(Asset.project_id == -1)
    assets_result = await db.execute(asset_query.limit(5))

    finding_query = select(Finding).where(Finding.title.ilike(pattern))
    if not is_admin and project_ids:
        finding_query = finding_query.where(Finding.project_id.in_(project_ids))
    elif not is_admin:
        finding_query = finding_query.where(Finding.project_id == -1)
    findings_result = await db.execute(finding_query.limit(5))

    knowledge_result = await db.execute(
        select(VulnKnowledge).where(
            VulnKnowledge.title.ilike(pattern) | VulnKnowledge.cve_id.ilike(pattern)
        ).limit(5)
    )

    return {
        "projects": projects_list,
        "assets": [{"id": a.id, "host": a.host, "project_id": a.project_id, "type": "asset"} for a in assets_result.scalars()],
        "findings": [{"id": f.id, "title": f.title, "severity": f.severity, "project_id": f.project_id, "type": "finding"} for f in findings_result.scalars()],
        "knowledge": [{"id": k.id, "title": k.title, "cve_id": k.cve_id, "type": "knowledge"} for k in knowledge_result.scalars()],
    }
