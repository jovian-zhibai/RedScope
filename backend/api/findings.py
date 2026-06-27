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
    _=Depends(require_project),
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
    VALID_SEVERITY = {"critical", "high", "medium", "low", "info"}
    VALID_FIX_STATUS = {"unfixed", "fixing", "fixed", "reopen", "accepted", "merged"}
    for field, value in req.items():
        if field not in UPDATABLE_FIELDS:
            continue
        if field == "severity" and value not in VALID_SEVERITY:
            raise HTTPException(400, f"无效的严重程度: {value}")
        if field == "fix_status" and value not in VALID_FIX_STATUS:
            raise HTTPException(400, f"无效的修复状态: {value}")
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


@router.post("/{finding_id}/rescan")
async def rescan_finding(project_id: int, finding_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    """Re-scan a specific finding to verify if it's been fixed."""
    finding = await db.get(Finding, finding_id)
    if not finding or finding.project_id != project_id:
        raise HTTPException(404, "漏洞不存在")

    host = ""
    detail = finding.detail or ""
    title = finding.title or ""
    import re
    matches = re.findall(r'([\w.\-]+:\d+)', f"{title} {detail}")
    if matches:
        host = matches[0]
    elif "Host:" in detail:
        host = detail.split("Host:")[-1].strip().split("\n")[0].strip()

    if not host:
        raise HTTPException(400, "无法从漏洞信息中提取目标地址")

    from backend.models.scan_task import ScanTask
    task = ScanTask(
        project_id=project_id,
        task_name=f"复测: {finding.title[:50]}",
        scan_strategy="standard",
        engines=["nuclei"],
        target_assets=[host],
        total_targets=1,
    )
    db.add(task)
    await db.flush()

    from backend.tasks.scan_worker import run_scan_task
    try:
        run_scan_task.delay(task.id)
    except Exception:
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, run_scan_task, task.id)

    return {"scan_id": task.id, "target": host, "message": "复测任务已创建"}


@router.post("/link-assets")
async def link_findings_to_assets(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    """Backfill: associate unlinked findings with matching assets by host."""
    from backend.models.asset import Asset
    import socket, re

    unlinked = await db.execute(
        select(Finding).where(Finding.project_id == project_id, Finding.asset_id == None, Finding.deleted_at == None)
    )
    findings = unlinked.scalars().all()

    assets_result = await db.execute(select(Asset).where(Asset.project_id == project_id))
    assets = assets_result.scalars().all()

    asset_by_ip_port = {}
    for a in assets:
        asset_by_ip_port[(a.host, a.port)] = a

    dns_cache = {}

    linked = 0
    for f in findings:
        text = f"{f.title or ''} {f.detail or ''}"

        # Try to extract host:port from finding text
        matches = re.findall(r'([\w.\-]+):(\d+)', text)
        for host, port_str in matches:
            port = int(port_str)
            # Direct IP match
            if (host, port) in asset_by_ip_port:
                f.asset_id = asset_by_ip_port[(host, port)].id
                linked += 1
                break
            # DNS resolve and match
            if host not in dns_cache:
                try:
                    dns_cache[host] = socket.gethostbyname(host)
                except Exception:
                    dns_cache[host] = None
            resolved = dns_cache[host]
            if resolved and (resolved, port) in asset_by_ip_port:
                f.asset_id = asset_by_ip_port[(resolved, port)].id
                linked += 1
                break

    await db.flush()
    return {"total_unlinked": len(findings), "linked": linked}
