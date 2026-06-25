from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.vuln_knowledge import VulnKnowledge

router = APIRouter()


class VulnSearch(BaseModel):
    keyword: str | None = None
    vendor: str | None = None
    severity: str | None = None
    has_poc: bool | None = None


@router.get("")
async def search_knowledge(
    keyword: str | None = None,
    vendor: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = select(VulnKnowledge).order_by(VulnKnowledge.updated_at.desc()).limit(limit)
    if keyword:
        query = query.where(VulnKnowledge.title.ilike(f"%{keyword}%"))
    if vendor:
        query = query.where(VulnKnowledge.affected_vendor.ilike(f"%{vendor}%"))
    if severity:
        query = query.where(VulnKnowledge.severity == severity)

    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": [
        {
            "id": v.id, "cve_id": v.cve_id, "cnvd_id": v.cnvd_id, "title": v.title,
            "severity": v.severity, "cvss_score": float(v.cvss_score) if v.cvss_score else None,
            "affected_software": v.affected_software, "affected_vendor": v.affected_vendor,
            "weapon_stage": v.weapon_stage, "has_poc": v.has_poc, "has_exp": v.has_exp,
            "tags": v.tags, "published_at": v.published_at.isoformat() if v.published_at else None,
        }
        for v in items
    ]}


@router.post("")
async def create_knowledge(req: dict, request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role not in ("admin", "leader"):
        raise HTTPException(403, "仅管理员/组长可添加漏洞情报")
    allowed_fields = {"cve_id", "cnvd_id", "title", "severity", "cvss_score", "description",
                      "solution", "affected_software", "affected_vendor", "affected_version",
                      "vuln_type", "weapon_stage", "has_poc", "has_exp", "tags"}
    vuln = VulnKnowledge(**{k: v for k, v in req.items() if k in allowed_fields})
    db.add(vuln)
    await db.flush()
    return {"id": vuln.id, "title": vuln.title}


@router.post("/fetch-nvd")
async def trigger_nvd_fetch(request: Request):
    if request.state.role not in ("admin", "leader"):
        raise HTTPException(403, "仅管理员/组长可触发")
    from backend.tasks.scan_worker import sync_vulnerability_intel
    sync_vulnerability_intel.delay()
    return {"status": "triggered", "added": 0, "message": "NVD 抓取任务已提交后台执行"}


@router.post("/fetch-cnvd")
async def trigger_cnvd_fetch(request: Request):
    if request.state.role not in ("admin", "leader"):
        raise HTTPException(403, "仅管理员/组长可触发")
    from backend.tasks.scan_worker import sync_vulnerability_intel
    sync_vulnerability_intel.delay()
    return {"status": "triggered", "added": 0, "message": "CNVD 抓取任务已提交后台执行"}
