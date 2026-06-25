from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.project import Project
from backend.models.asset import Asset
from backend.models.finding import Finding

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    mode: str  # combat / range / research
    client_name: str | None = None
    client_contact: str | None = None
    emergency_contact: str | None = None
    auth_start_date: str | None = None
    auth_end_date: str | None = None
    scan_intensity: str = "standard"
    max_concurrency: int = 50
    sensitive_data_policy: str = "mask"


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    scan_intensity: str | None = None
    max_concurrency: int | None = None


@router.get("")
async def list_projects(status: str | None = None, request: Request = None, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    query = select(
        Project,
        func.count(Asset.id.distinct()).label("asset_count"),
        func.count(Finding.id.distinct()).label("finding_count"),
    ).outerjoin(Asset, Asset.project_id == Project.id).outerjoin(
        Finding, Finding.project_id == Project.id
    ).group_by(Project.id).order_by(Project.updated_at.desc())

    if status:
        query = query.where(Project.status == status)

    # Tenant isolation: non-admin users only see projects in their tenant or created by them
    if request and hasattr(request.state, 'role') and request.state.role != 'admin':
        tenant_id = getattr(request.state, 'tenant_id', None)
        user_id = getattr(request.state, 'user_id', 0)
        if tenant_id:
            query = query.where((Project.tenant_id == tenant_id) | (Project.created_by == user_id))
        else:
            query = query.where(Project.created_by == user_id)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for p, asset_count, finding_count in rows:
        items.append({
            "id": p.id, "name": p.name, "mode": p.mode, "status": p.status,
            "client_name": p.client_name, "description": p.description,
            "asset_count": asset_count, "finding_count": finding_count,
            "auth_end_date": str(p.auth_end_date) if p.auth_end_date else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })
    return {"items": items, "total": len(items)}


@router.post("")
async def create_project(req: ProjectCreate, request: Request, db: AsyncSession = Depends(get_db)):
    from datetime import date
    project = Project(
        name=req.name,
        description=req.description,
        mode=req.mode,
        client_name=req.client_name,
        client_contact=req.client_contact,
        emergency_contact=req.emergency_contact,
        scan_intensity=req.scan_intensity,
        max_concurrency=req.max_concurrency,
        sensitive_data_policy=req.sensitive_data_policy,
        created_by=request.state.user_id,
        tenant_id=getattr(request.state, 'tenant_id', None),
    )
    if req.auth_start_date:
        project.auth_start_date = date.fromisoformat(req.auth_start_date)
    if req.auth_end_date:
        project.auth_end_date = date.fromisoformat(req.auth_end_date)

    db.add(project)
    await db.flush()
    return {"id": project.id, "name": project.name, "mode": project.mode}


@router.get("/{project_id}")
async def get_project(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    asset_count = await db.scalar(select(func.count()).where(Asset.project_id == project_id))
    finding_count = await db.scalar(select(func.count()).where(Finding.project_id == project_id))

    return {
        "id": project.id, "name": project.name, "mode": project.mode,
        "status": project.status, "description": project.description,
        "client_name": project.client_name, "client_contact": project.client_contact,
        "emergency_contact": project.emergency_contact,
        "scan_intensity": project.scan_intensity, "max_concurrency": project.max_concurrency,
        "sensitive_data_policy": project.sensitive_data_policy,
        "auth_start_date": str(project.auth_start_date) if project.auth_start_date else None,
        "auth_end_date": str(project.auth_end_date) if project.auth_end_date else None,
        "asset_count": asset_count, "finding_count": finding_count,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


@router.put("/{project_id}")
async def update_project(project_id: int, req: ProjectUpdate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.flush()
    return {"id": project.id, "status": "updated"}


@router.post("/{project_id}/emergency-stop")
async def emergency_stop(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.core.engine_orchestrator import orchestrator
    from backend.models.scan_task import ScanTask
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    result = await db.execute(
        select(ScanTask).where(ScanTask.project_id == project_id, ScanTask.status == "running")
    )
    running_tasks = result.scalars().all()
    for task in running_tasks:
        for key in list(orchestrator._running_jobs.keys()):
            if key.startswith(f"{task.id}_"):
                await orchestrator.stop_engine(key)
        task.status = "stopped"
        task.stopped_reason = "项目紧急停止"

    project.status = "paused"
    await db.flush()
    return {"status": "stopped", "message": f"已停止 {len(running_tasks)} 个扫描任务"}
