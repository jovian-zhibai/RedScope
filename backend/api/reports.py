from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.operational import Report

router = APIRouter()


class ReportGenerateRequest(BaseModel):
    title: str = "渗透测试报告"
    report_type: str = "pentest"
    include_sections: list[str] = ["summary", "findings", "statistics"]
    compliance_std: str | None = None
    format: str = "docx"


@router.get("")
async def list_reports(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Report).where(Report.project_id == project_id).order_by(Report.created_at.desc())
    )
    reports = result.scalars().all()
    return {"items": [
        {
            "id": r.id, "title": r.title, "report_type": r.report_type,
            "format": r.format, "compliance_std": r.compliance_std,
            "file_path": r.file_path,
            "has_file": bool(r.file_path and Path(r.file_path).exists()),
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]}


@router.get("/{report_id}/download")
async def download_report(project_id: int, report_id: int, token: str = None, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    report = await db.get(Report, report_id)
    if not report or report.project_id != project_id:
        raise HTTPException(404, "报告不存在")
    if not report.file_path or not Path(report.file_path).exists():
        raise HTTPException(404, "报告文件未生成或已被清理")

    filename = f"{report.title}.{report.format or 'docx'}"
    return FileResponse(
        report.file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/{report_id}/preview")
async def preview_report(project_id: int, report_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    """Return report content as structured JSON for in-browser preview."""
    report = await db.get(Report, report_id)
    if not report or report.project_id != project_id:
        raise HTTPException(404, "报告不存在")

    from backend.models.project import Project
    from backend.models.finding import Finding
    from backend.models.asset import Asset
    from sqlalchemy import select

    project = await db.get(Project, project_id)
    findings_result = await db.execute(
        select(Finding).where(
            Finding.project_id == project_id,
            Finding.is_false_positive == False,
            Finding.deleted_at == None,
        ).order_by(Finding.severity)
    )
    findings = findings_result.scalars().all()
    assets_result = await db.execute(
        select(Asset).where(Asset.project_id == project_id, Asset.deleted_at == None)
    )
    assets = assets_result.scalars().all()

    sev_counts = {}
    for f in findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

    return {
        "title": report.title,
        "project_name": project.name if project else "",
        "client_name": project.client_name if project else "",
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "summary": {
            "total": len(findings),
            "critical": sev_counts.get("critical", 0),
            "high": sev_counts.get("high", 0),
            "medium": sev_counts.get("medium", 0),
            "low": sev_counts.get("low", 0),
            "info": sev_counts.get("info", 0),
            "asset_count": len(assets),
        },
        "findings": [
            {
                "title": f.title, "severity": f.severity, "vuln_type": f.vuln_type,
                "cvss_score": float(f.cvss_score) if f.cvss_score else None,
                "description": f.description, "detail": f.detail, "solution": f.solution,
            }
            for f in findings
        ],
        "assets": [
            {"host": a.host, "port": a.port, "application": a.application or "", "importance": a.importance}
            for a in assets[:50]
        ],
    }


@router.post("/generate")
async def generate_report(project_id: int, req: ReportGenerateRequest, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    report = Report(
        project_id=project_id,
        title=req.title,
        report_type=req.report_type,
        include_sections=req.include_sections,
        compliance_std=req.compliance_std,
        format=req.format,
    )
    db.add(report)
    await db.flush()

    from backend.tasks.report_task import generate_report_task
    generate_report_task.delay(report.id, project_id)

    return {"id": report.id, "status": "generating", "message": "报告生成任务已提交"}
