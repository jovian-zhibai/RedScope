"""Multi-tenant isolation: tenant management and data isolation middleware."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, event
from sqlalchemy.orm import Session
from backend.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(64), unique=True, nullable=False)  # url-friendly identifier
    description = Column(String(512))
    max_users = Column(Integer, default=50)
    max_projects = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TenantUser(Base):
    __tablename__ = "tenant_users"

    tenant_id = Column(Integer, ForeignKey("tenants.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role = Column(String(20), default="member")  # owner / admin / member
    joined_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── Tenant-aware query helpers ───────────────────────────

def get_user_tenant_id(db: Session, user_id: int) -> int | None:
    result = db.execute(
        TenantUser.__table__.select().where(TenantUser.user_id == user_id)
    )
    row = result.first()
    return row.tenant_id if row else None


def tenant_filter(query, model, tenant_id: int):
    if hasattr(model, "tenant_id"):
        return query.where(model.tenant_id == tenant_id)
    return query
