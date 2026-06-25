"""Multi-tenant management API — admin only."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.tenant import Tenant, TenantUser
from backend.models.user import User
from backend.models.project import Project
from backend.core.rbac import require_admin

router = APIRouter()


class TenantCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    max_users: int = 50
    max_projects: int = 100


class TenantAddUser(BaseModel):
    user_id: int
    role: str = "member"


@router.get("")
async def list_tenants(_=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at))
    tenants = result.scalars().all()
    items = []
    for t in tenants:
        user_count = await db.scalar(select(func.count()).where(TenantUser.tenant_id == t.id))
        items.append({
            "id": t.id, "name": t.name, "slug": t.slug,
            "description": t.description, "is_active": t.is_active,
            "max_users": t.max_users, "max_projects": t.max_projects,
            "user_count": user_count,
        })
    return {"items": items}


@router.post("")
async def create_tenant(req: TenantCreate, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Tenant).where(Tenant.slug == req.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "租户标识已存在")

    tenant = Tenant(**req.model_dump())
    db.add(tenant)
    await db.flush()
    return {"id": tenant.id, "name": tenant.name, "slug": tenant.slug}


@router.post("/{tenant_id}/users")
async def add_user_to_tenant(tenant_id: int, req: TenantAddUser, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, "租户不存在")

    user_count = await db.scalar(select(func.count()).where(TenantUser.tenant_id == tenant_id))
    if user_count >= tenant.max_users:
        raise HTTPException(400, f"租户用户数已达上限({tenant.max_users})")

    tu = TenantUser(tenant_id=tenant_id, user_id=req.user_id, role=req.role)
    db.add(tu)
    await db.flush()
    return {"status": "added"}


@router.get("/{tenant_id}/users")
async def list_tenant_users(tenant_id: int, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TenantUser, User).join(User, TenantUser.user_id == User.id)
        .where(TenantUser.tenant_id == tenant_id)
    )
    items = []
    for tu, user in result.all():
        items.append({
            "user_id": user.id, "username": user.username,
            "display_name": user.display_name, "role": tu.role,
        })
    return {"items": items}


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: int, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, "租户不存在")
    tenant.is_active = False
    await db.flush()
    return {"status": "disabled"}


@router.delete("/{tenant_id}/users/{user_id}")
async def remove_user_from_tenant(tenant_id: int, user_id: int, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TenantUser).where(TenantUser.tenant_id == tenant_id, TenantUser.user_id == user_id)
    )
    tu = result.scalar_one_or_none()
    if not tu:
        raise HTTPException(404, "用户不在该租户中")
    await db.delete(tu)
    await db.flush()
    return {"status": "removed"}
