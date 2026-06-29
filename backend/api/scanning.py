from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.scan_task import ScanTask
from backend.core.boundary_checker import load_boundary_checker
from backend.utils.cloud_provider import check_cloud_compliance

router = APIRouter()


class ScanCreate(BaseModel):
    task_name: str
    scan_strategy: str = "standard"  # quick / standard / deep / passive
    engines: list[str] = []
    targets: list[str] = []


@router.get("")
async def list_scans(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScanTask).where(ScanTask.project_id == project_id).order_by(ScanTask.created_at.desc())
    )
    tasks = result.scalars().all()
    return {"items": [
        {
            "id": t.id, "task_name": t.task_name, "scan_strategy": t.scan_strategy,
            "engines": t.engines, "status": t.status, "progress": t.progress,
            "total_targets": t.total_targets, "scanned_count": t.scanned_count,
            "vulns_found": t.vulns_found,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]}


@router.post("")
async def create_scan(project_id: int, req: ScanCreate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    # Input sanitization first
    from backend.utils.sanitizer import sanitize_targets
    try:
        clean_targets = sanitize_targets(req.targets)
    except ValueError as e:
        raise HTTPException(400, detail={"message": f"目标格式非法: {e}"})

    checker = await load_boundary_checker(db, project_id)

    violations = []
    for target in clean_targets:
        result = checker.check_target(target)
        if not result.allowed:
            violations.append({"target": target, "reason": result.reason})

    if violations:
        raise HTTPException(400, detail={"message": "部分目标不在授权范围内", "violations": violations})

    # OPSEC check
    from backend.core.opsec_monitor import check_scan_opsec
    from backend.models.project import Project
    project = await db.get(Project, project_id)
    from datetime import datetime as dt
    now = dt.now()
    is_work_hours = 9 <= now.hour <= 18 and now.weekday() < 5
    opsec_warnings = []
    for engine in (req.engines or ["nuclei"]):
        warnings = check_scan_opsec(
            engine_name=engine,
            concurrency=project.max_concurrency if project else 50,
            target_count=len(clean_targets),
            is_work_hours=is_work_hours,
            project_mode=project.mode if project else "combat",
        )
        opsec_warnings.extend([{"level": w.level, "category": w.category, "message": w.message, "suggestion": w.suggestion} for w in warnings])

    task = ScanTask(
        project_id=project_id,
        task_name=req.task_name,
        scan_strategy=req.scan_strategy,
        engines=req.engines,
        target_assets=clean_targets,
        total_targets=len(clean_targets),
    )
    db.add(task)
    await db.flush()

    cloud_warnings = check_cloud_compliance(req.targets)

    from backend.tasks.scan_worker import run_scan_task
    try:
        run_scan_task.delay(task.id)
    except Exception as e:
        from backend.core.error_handler import logger
        logger.warning(f"Celery dispatch failed ({e}), running scan synchronously")
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, run_scan_task.run, task.id)

    result = {"id": task.id, "status": "pending", "message": "扫描任务已创建并开始执行"}
    if cloud_warnings:
        result["cloud_warnings"] = cloud_warnings
    if opsec_warnings:
        result["opsec_warnings"] = opsec_warnings
    return result


@router.post("/{scan_id}/stop")
async def stop_scan(project_id: int, scan_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    task = await db.get(ScanTask, scan_id)
    if not task or task.project_id != project_id:
        raise HTTPException(404, "任务不存在")

    from backend.models.scan_task import EngineRun
    import httpx, os

    result = await db.execute(
        select(EngineRun).where(EngineRun.scan_task_id == scan_id, EngineRun.status == "running")
    )
    running_runs = result.scalars().all()

    runner_url = os.environ.get("SCAN_RUNNER_URL", "http://scan-runner:9090")
    runner_secret = os.environ.get("RUNNER_SECRET", "")
    headers = {"X-Runner-Secret": runner_secret} if runner_secret else {}

    stopped = 0
    async with httpx.AsyncClient(timeout=10) as client:
        for run in running_runs:
            if run.runner_job_id:
                try:
                    await client.delete(f"{runner_url}/jobs/{run.runner_job_id}", headers=headers)
                    stopped += 1
                except Exception as e:
                    logging.getLogger("scanning").warning(f"Failed to stop runner job {run.runner_job_id}: {e}")
            run.status = "failed"
            run.error_message = "用户手动停止"

    task.status = "stopped"
    task.stopped_reason = "用户手动停止"
    await db.flush()
    return {"status": "stopped", "stopped_engines": stopped}


@router.get("/{scan_id}")
async def get_scan(project_id: int, scan_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.models.scan_task import EngineRun
    task = await db.get(ScanTask, scan_id)
    if not task or task.project_id != project_id:
        raise HTTPException(404, "任务不存在")

    engine_runs_result = await db.execute(
        select(EngineRun).where(EngineRun.scan_task_id == scan_id).order_by(EngineRun.started_at)
    )
    engine_runs = engine_runs_result.scalars().all()

    return {
        "id": task.id, "task_name": task.task_name, "scan_strategy": task.scan_strategy,
        "engines": task.engines, "status": task.status, "progress": task.progress,
        "total_targets": task.total_targets, "scanned_count": task.scanned_count,
        "vulns_found": task.vulns_found, "stopped_reason": task.stopped_reason,
        "target_assets": task.target_assets,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "engine_runs": [
            {"id": r.id, "engine_name": r.engine_name, "status": r.status,
             "vulns_found": r.vulns_found, "error_message": r.error_message,
             "runner_job_id": r.runner_job_id,
             "started_at": r.started_at.isoformat() if r.started_at else None,
             "finished_at": r.finished_at.isoformat() if r.finished_at else None}
            for r in engine_runs
        ],
    }


@router.get("/{scan_id}/logs/{job_id}")
async def get_scan_logs(project_id: int, scan_id: int, job_id: str, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    task = await db.get(ScanTask, scan_id)
    if not task or task.project_id != project_id:
        raise HTTPException(404, "任务不存在")

    from pathlib import Path
    # Prevent path traversal: reject .., /, \ in job_id
    if ".." in job_id or "/" in job_id or "\\" in job_id:
        raise HTTPException(400, "job_id 格式非法")
    output_base = Path("/app/output").resolve()
    output_dir = (output_base / job_id).resolve()
    if not str(output_dir).startswith(str(output_base)):
        raise HTTPException(403, "非法路径")

    stderr_file = output_dir / "stderr.log"
    stdout_file = output_dir / "stdout.log"

    stderr = stderr_file.read_text(errors="replace")[:5000] if stderr_file.exists() else ""
    stdout = stdout_file.read_text(errors="replace")[:5000] if stdout_file.exists() else ""

    return {"stderr": stderr, "stdout": stdout}
