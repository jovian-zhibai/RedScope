from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from backend.config import get_settings
from backend.core.auth_middleware import auth_middleware
from backend.core.error_handler import global_exception_handler, request_logging_middleware, logger
from backend.core.rate_limiter import rate_limit_middleware
from backend.core.audit_logger import audit_log_middleware
from backend.database import get_db, init_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api import (
    auth, projects, scope, assets, scanning, findings, knowledge, plugins,
    reports, operational, terminal, manual_testing, baseline,
    tenants, client_portal, redblue, workflow, wiring,
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

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(projects.router, prefix="/api/projects", tags=["项目管理"])
app.include_router(scope.router, prefix="/api/projects/{project_id}/scope", tags=["边界管理"])
app.include_router(assets.router, prefix="/api/projects/{project_id}/assets", tags=["资产管理"])
app.include_router(scanning.router, prefix="/api/projects/{project_id}/scans", tags=["扫描任务"])
app.include_router(findings.router, prefix="/api/projects/{project_id}/findings", tags=["漏洞管理"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["漏洞情报"])
app.include_router(plugins.router, prefix="/api/plugins", tags=["插件管理"])
app.include_router(reports.router, prefix="/api/projects/{project_id}/reports", tags=["报告生成"])
app.include_router(operational.router, prefix="/api/projects/{project_id}/ops", tags=["作战管理"])
app.include_router(terminal.router, prefix="/ws", tags=["终端"])
app.include_router(manual_testing.router, prefix="/api/testing", tags=["手工测试"])
app.include_router(baseline.router, prefix="/api/baseline", tags=["基线合规"])
app.include_router(tenants.router, prefix="/api/tenants", tags=["多租户"])
app.include_router(client_portal.router, prefix="/api/portal", tags=["客户门户"])
app.include_router(redblue.router, prefix="/api/projects/{project_id}/redblue", tags=["红蓝对抗"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["工单审批"])
app.include_router(wiring.router, prefix="/api", tags=["核心能力"])


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
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url)
        r.ping()
        status["redis"] = "ok"
    except Exception:
        status["redis"] = "error"

    all_ok = status.get("database") == "ok" and status.get("redis") == "ok"
    status["status"] = "ok" if all_ok else "degraded"
    return status


@app.get("/api/search")
async def global_search(q: str = "", db: AsyncSession = Depends(get_db)):
    """Global search across projects, assets, findings, and knowledge base."""
    from backend.models.project import Project
    from backend.models.asset import Asset
    from backend.models.finding import Finding
    from backend.models.vuln_knowledge import VulnKnowledge

    if not q or len(q) < 2:
        return {"projects": [], "assets": [], "findings": [], "knowledge": []}

    pattern = f"%{q}%"

    projects = await db.execute(
        select(Project).where(Project.name.ilike(pattern) | Project.client_name.ilike(pattern)).limit(5)
    )
    assets_result = await db.execute(
        select(Asset).where(Asset.host.ilike(pattern) | Asset.application.ilike(pattern)).limit(5)
    )
    findings_result = await db.execute(
        select(Finding).where(Finding.title.ilike(pattern)).limit(5)
    )
    knowledge_result = await db.execute(
        select(VulnKnowledge).where(
            VulnKnowledge.title.ilike(pattern) | VulnKnowledge.cve_id.ilike(pattern)
        ).limit(5)
    )

    return {
        "projects": [{"id": p.id, "name": p.name, "type": "project"} for p in projects.scalars()],
        "assets": [{"id": a.id, "host": a.host, "project_id": a.project_id, "type": "asset"} for a in assets_result.scalars()],
        "findings": [{"id": f.id, "title": f.title, "severity": f.severity, "project_id": f.project_id, "type": "finding"} for f in findings_result.scalars()],
        "knowledge": [{"id": k.id, "title": k.title, "cve_id": k.cve_id, "type": "knowledge"} for k in knowledge_result.scalars()],
    }
