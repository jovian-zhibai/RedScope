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
        esc_kw = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(VulnKnowledge.title.ilike(f"%{esc_kw}%"))
    if vendor:
        esc_vd = vendor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(VulnKnowledge.affected_vendor.ilike(f"%{esc_vd}%"))
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


class KnowledgeCreate(BaseModel):
    cve_id: str | None = None
    cnvd_id: str | None = None
    title: str
    severity: str = "medium"
    cvss_score: float | None = None
    description: str | None = None
    solution: str | None = None
    affected_software: str | None = None
    affected_vendor: str | None = None
    affected_versions: str | None = None
    vuln_type: str | None = None
    weapon_stage: str | None = None
    has_poc: bool = False
    has_exp: bool = False
    tags: list | None = None
    fingerprints: list | None = None


@router.post("")
async def create_knowledge(req: KnowledgeCreate, request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role not in ("admin", "leader"):
        raise HTTPException(403, "仅管理员/组长可添加漏洞情报")
    vuln = VulnKnowledge(**req.model_dump(exclude_unset=True))
    db.add(vuln)
    await db.flush()
    return {"id": vuln.id, "title": vuln.title}


@router.post("/fetch-nvd")
async def trigger_nvd_fetch(request: Request):
    if request.state.role not in ("admin", "leader"):
        raise HTTPException(403, "仅管理员/组长可触发")

    from backend.config import get_settings
    s = get_settings()
    if not s.llm_api_key:
        try:
            from backend.database_sync import SyncSession
            from backend.models.operational import SystemSetting
            with SyncSession() as db:
                result = db.execute(SystemSetting.__table__.select().where(SystemSetting.__table__.c.key == "nvd_api_key"))
                row = result.first()
                if not row or not row.value:
                    raise HTTPException(400, "请先在 设置→系统配置 中配置 NVD API Key")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(400, "请先配置 NVD API Key")

    from backend.tasks.scan_worker import sync_vulnerability_intel
    sync_vulnerability_intel.delay()
    return {"status": "triggered", "message": "NVD 抓取任务已提交后台执行，请稍后刷新查看"}


@router.post("/fetch-cnvd")
async def trigger_cnvd_fetch(request: Request):
    if request.state.role not in ("admin", "leader"):
        raise HTTPException(403, "仅管理员/组长可触发")
    from backend.tasks.scan_worker import sync_vulnerability_intel
    sync_vulnerability_intel.delay()
    return {"status": "triggered", "added": 0, "message": "CNVD 抓取任务已提交后台执行"}
