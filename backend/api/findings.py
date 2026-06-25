from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.finding import Finding

router = APIRouter()


class FindingCreate(BaseModel):
    asset_id: int | None = None
    title: str
    vuln_type: str | None = None
    severity: str = "medium"
    cvss_score: float | None = None
    description: str | None = None
    detail: str | None = None
    solution: str | None = None
    found_by: str = "manual"
    evidence: dict | None = None


@router.get("")
async def list_findings(
    project_id: int,
    severity: str | None = None,
    fix_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    from backend.core.pagination import paginate
    query = select(Finding).where(Finding.project_id == project_id, Finding.deleted_at == None).order_by(Finding.created_at.desc())
    if severity:
        query = query.where(Finding.severity == severity)
    if fix_status:
        query = query.where(Finding.fix_status == fix_status)

    paged = await paginate(db, query, page, page_size)
    findings = paged["items"]
    return {
        "total": paged["total"], "page": paged["page"],
        "page_size": paged["page_size"], "total_pages": paged["total_pages"],
        "items": [
        {
            "id": f.id, "title": f.title, "vuln_type": f.vuln_type,
            "severity": f.severity, "cvss_score": float(f.cvss_score) if f.cvss_score else None,
            "combined_risk_score": float(f.combined_risk_score) if f.combined_risk_score else None,
            "asset_id": f.asset_id, "fix_status": f.fix_status,
            "is_verified": f.is_verified, "is_false_positive": f.is_false_positive,
            "found_by": f.found_by,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in findings
    ]}


@router.post("")
async def create_finding(project_id: int, req: FindingCreate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    finding = Finding(
        project_id=project_id,
        asset_id=req.asset_id,
        title=req.title,
        vuln_type=req.vuln_type,
        severity=req.severity,
        cvss_score=req.cvss_score,
        description=req.description,
        detail=req.detail,
        solution=req.solution,
        found_by=req.found_by,
        evidence=req.evidence,
    )
    db.add(finding)
    await db.flush()
    return {"id": finding.id, "title": finding.title}


@router.get("/stats")
async def finding_stats(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    severities = {}
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = await db.scalar(
            select(func.count()).where(Finding.project_id == project_id, Finding.severity == sev, Finding.deleted_at == None)
        )
        severities[sev] = count

    total = sum(severities.values())
    unfixed = await db.scalar(
        select(func.count()).where(Finding.project_id == project_id, Finding.fix_status == "unfixed", Finding.deleted_at == None)
    )
    fixed = total - unfixed
    return {"total": total, "severities": severities, "unfixed": unfixed, "fixed": fixed, "fix_rate": round(fixed / total * 100, 1) if total > 0 else 0}


@router.put("/{finding_id}")
async def update_finding(project_id: int, finding_id: int, req: dict, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    finding = await db.get(Finding, finding_id)
    if not finding or finding.project_id != project_id:
        raise HTTPException(404, "漏洞不存在")
    UPDATABLE_FIELDS = {"title", "vuln_type", "severity", "cvss_score", "description", "detail",
                        "solution", "fix_status", "is_verified", "is_false_positive", "evidence", "attck_techniques"}
    for field, value in req.items():
        if field in UPDATABLE_FIELDS:
            setattr(finding, field, value)
    await db.flush()
    return {"id": finding.id, "status": "updated"}


@router.get("/{finding_id}")
async def get_finding(project_id: int, finding_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    finding = await db.get(Finding, finding_id)
    if not finding or finding.project_id != project_id:
        raise HTTPException(404, "漏洞不存在")
    return {
        "id": finding.id, "title": finding.title, "vuln_type": finding.vuln_type,
        "severity": finding.severity, "cvss_score": float(finding.cvss_score) if finding.cvss_score else None,
        "description": finding.description, "detail": finding.detail, "solution": finding.solution,
        "asset_id": finding.asset_id, "found_by": finding.found_by,
        "is_verified": finding.is_verified, "is_false_positive": finding.is_false_positive,
        "fix_status": finding.fix_status, "evidence": finding.evidence,
        "attck_techniques": finding.attck_techniques,
        "created_at": finding.created_at.isoformat() if finding.created_at else None,
    }


@router.delete("/{finding_id}")
async def delete_finding(project_id: int, finding_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    finding = await db.get(Finding, finding_id)
    if not finding or finding.project_id != project_id:
        raise HTTPException(404, "漏洞不存在")
    finding.deleted_at = datetime.now()
    await db.flush()
    return {"status": "deleted"}
