from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.asset import Asset

router = APIRouter()


class AssetCreate(BaseModel):
    asset_type: str
    host: str
    port: int | None = None
    protocol: str | None = None
    url: str | None = None
    importance: str = "normal"
    tags: list[str] = []


@router.get("")
async def list_assets(
    project_id: int,
    scope_status: str | None = None,
    importance: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    from backend.core.pagination import paginate
    query = select(Asset).where(Asset.project_id == project_id, Asset.deleted_at == None).order_by(Asset.last_seen_at.desc())
    if scope_status:
        query = query.where(Asset.scope_status == scope_status)
    if importance:
        query = query.where(Asset.importance == importance)

    paged = await paginate(db, query, page, page_size)
    assets = paged["items"]
    return {
        "total": paged["total"], "page": paged["page"],
        "page_size": paged["page_size"], "total_pages": paged["total_pages"],
        "items": [
        {
            "id": a.id, "asset_type": a.asset_type, "host": a.host, "port": a.port,
            "protocol": a.protocol, "url": a.url, "os": a.os, "server": a.server,
            "framework": a.framework, "application": a.application, "app_version": a.app_version,
            "scope_status": a.scope_status, "importance": a.importance,
            "is_alive": a.is_alive, "discovered_by": a.discovered_by,
            "tags": a.tags or [],
            "first_seen_at": a.first_seen_at.isoformat() if a.first_seen_at else None,
            "last_seen_at": a.last_seen_at.isoformat() if a.last_seen_at else None,
        }
        for a in assets
    ]}


@router.post("")
async def create_asset(project_id: int, req: AssetCreate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    asset = Asset(
        project_id=project_id,
        asset_type=req.asset_type,
        host=req.host,
        port=req.port,
        protocol=req.protocol,
        url=req.url,
        importance=req.importance,
        tags=req.tags,
        discovered_by="manual",
    )
    db.add(asset)
    await db.flush()
    return {"id": asset.id, "host": asset.host}


@router.get("/stats")
async def asset_stats(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).where(Asset.project_id == project_id))
    alive = await db.scalar(select(func.count()).where(Asset.project_id == project_id, Asset.is_alive == True))
    return {"total": total, "alive": alive, "dead": total - alive}


@router.put("/{asset_id}")
async def update_asset(project_id: int, asset_id: int, req: dict, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    asset = await db.get(Asset, asset_id)
    if not asset or asset.project_id != project_id:
        raise HTTPException(404, "资产不存在")
    for field, value in req.items():
        if hasattr(asset, field):
            setattr(asset, field, value)
    await db.flush()
    return {"id": asset.id, "status": "updated"}


@router.delete("/{asset_id}")
async def delete_asset(project_id: int, asset_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    asset = await db.get(Asset, asset_id)
    if not asset or asset.project_id != project_id:
        raise HTTPException(404, "资产不存在")
    asset.deleted_at = datetime.now()
    await db.flush()
    return {"status": "deleted"}
