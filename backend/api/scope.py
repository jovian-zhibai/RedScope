from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.project import ScopeRule, ScopeChangeLog

router = APIRouter()


class ScopeRuleCreate(BaseModel):
    rule_type: str  # include / exclude
    target_type: str  # domain / ip / cidr / url / port
    target_value: str
    description: str | None = None


@router.get("")
async def list_scope_rules(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScopeRule).where(ScopeRule.project_id == project_id).order_by(ScopeRule.created_at)
    )
    rules = result.scalars().all()
    return {"items": [
        {"id": r.id, "rule_type": r.rule_type, "target_type": r.target_type,
         "target_value": r.target_value, "description": r.description,
         "is_active": r.is_active, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rules
    ]}


@router.post("")
async def create_scope_rule(project_id: int, req: ScopeRuleCreate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    rule = ScopeRule(
        project_id=project_id,
        rule_type=req.rule_type,
        target_type=req.target_type,
        target_value=req.target_value,
        description=req.description,
    )
    db.add(rule)

    log = ScopeChangeLog(
        project_id=project_id, action="add",
        rule_type=req.rule_type, target_value=req.target_value,
        reason=f"新增{req.rule_type}规则: {req.target_value}",
    )
    db.add(log)
    await db.flush()
    return {"id": rule.id, "status": "created"}


@router.delete("/{rule_id}")
async def delete_scope_rule(project_id: int, rule_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    rule = await db.get(ScopeRule, rule_id)
    if not rule or rule.project_id != project_id:
        raise HTTPException(404, "规则不存在")

    log = ScopeChangeLog(
        project_id=project_id, action="remove",
        rule_type=rule.rule_type, target_value=rule.target_value,
        reason=f"删除规则: {rule.target_value}",
    )
    db.add(log)
    await db.delete(rule)
    await db.flush()
    return {"status": "deleted"}


@router.get("/changelog")
async def scope_changelog(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScopeChangeLog).where(ScopeChangeLog.project_id == project_id)
        .order_by(ScopeChangeLog.changed_at.desc())
    )
    logs = result.scalars().all()
    return {"items": [
        {"id": l.id, "action": l.action, "rule_type": l.rule_type,
         "target_value": l.target_value, "reason": l.reason,
         "changed_at": l.changed_at.isoformat() if l.changed_at else None}
        for l in logs
    ]}
