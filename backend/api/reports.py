from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.operational import Report

router = APIRouter()


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
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]}


@router.post("/generate")
async def generate_report(project_id: int, req: dict, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    report = Report(
        project_id=project_id,
        title=req.get("title", "渗透测试报告"),
        report_type=req.get("report_type", "pentest"),
        include_sections=req.get("include_sections", ["summary", "findings", "statistics"]),
        compliance_std=req.get("compliance_std"),
        format=req.get("format", "docx"),
    )
    db.add(report)
    await db.flush()

    from backend.tasks.report_task import generate_report_task
    generate_report_task.delay(report.id, project_id)

    return {"id": report.id, "status": "generating", "message": "报告生成任务已提交"}
