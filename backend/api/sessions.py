"""Work sessions, screenshots, terminal recordings, risk acceptance, project templates API."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.operational import (
    WorkSession, Screenshot, TerminalRecording, RiskAcceptance, ProjectTemplate,
)

router = APIRouter()


# ─── Work Sessions ────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str = ""


@router.post("/projects/{project_id}/sessions/start")
async def start_session(project_id: int, req: SessionCreate, request: Request, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    active = await db.execute(
        select(WorkSession).where(
            WorkSession.project_id == project_id,
            WorkSession.user_id == request.state.user_id,
            WorkSession.status == "active",
        )
    )
    if active.scalar_one_or_none():
        raise HTTPException(400, "已有进行中的工作 Session，请先结束")

    session = WorkSession(
        project_id=project_id,
        user_id=request.state.user_id,
        title=req.title or f"工作 Session - {datetime.now().strftime('%m/%d %H:%M')}",
    )
    db.add(session)
    await db.flush()
    return {"id": session.id, "title": session.title, "started_at": session.started_at.isoformat()}


@router.post("/projects/{project_id}/sessions/{session_id}/end")
async def end_session(project_id: int, session_id: int, request: Request, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    session = await db.get(WorkSession, session_id)
    if not session or session.project_id != project_id:
        raise HTTPException(404, "Session 不存在")

    session.status = "completed"
    session.ended_at = datetime.now()

    # Auto-generate summary via AI if available
    try:
        from backend.ai.assistant import chat_with_assistant
        activities_text = "\n".join(
            [f"- {a.get('action', '')} {a.get('detail', '')}" for a in (session.activities or [])]
        )
        summary_prompt = (
            f"请为以下渗透测试工作 Session 生成简洁的中文摘要（3-5句话）：\n"
            f"项目: {project_id}\n扫描次数: {session.scans_run}\n发现漏洞: {session.findings_added}\n"
            f"笔记: {session.notes_count}\n截图: {session.screenshots_count}\n"
            f"活动记录:\n{activities_text}"
        )
        session.summary = await chat_with_assistant(summary_prompt)
    except Exception:
        session.summary = f"扫描 {session.scans_run} 次，发现 {session.findings_added} 个漏洞，{session.notes_count} 条笔记"

    await db.flush()
    return {"id": session.id, "status": "completed", "summary": session.summary}


@router.get("/projects/{project_id}/sessions")
async def list_sessions(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkSession).where(WorkSession.project_id == project_id).order_by(WorkSession.started_at.desc())
    )
    sessions = result.scalars().all()
    return {"items": [
        {"id": s.id, "title": s.title, "status": s.status, "user_id": s.user_id,
         "scans_run": s.scans_run, "findings_added": s.findings_added,
         "notes_count": s.notes_count, "screenshots_count": s.screenshots_count,
         "summary": s.summary,
         "started_at": s.started_at.isoformat() if s.started_at else None,
         "ended_at": s.ended_at.isoformat() if s.ended_at else None}
        for s in sessions
    ]}


class ActivityLog(BaseModel):
    action: str
    detail: str = ""


@router.post("/projects/{project_id}/sessions/{session_id}/activity")
async def log_activity(project_id: int, session_id: int, req: ActivityLog, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    session = await db.get(WorkSession, session_id)
    if not session or session.project_id != project_id:
        raise HTTPException(404)
    if not session.activities:
        session.activities = []
    session.activities = session.activities + [{"action": req.action, "detail": req.detail, "time": datetime.now().isoformat()}]
    await db.flush()
    return {"logged": True}


# ─── Screenshots ──────────────────────────────────────────

@router.post("/projects/{project_id}/screenshots")
async def upload_screenshot(
    project_id: int,
    request: Request,
    finding_id: int | None = None,
    asset_id: int | None = None,
    session_id: int | None = None,
    caption: str = "",
    file: UploadFile = File(...),
    _=Depends(require_project),
    db: AsyncSession = Depends(get_db),
):
    import os
    from pathlib import Path as P
    upload_dir = f"/app/output/screenshots/{project_id}"
    os.makedirs(upload_dir, exist_ok=True)

    import re
    # Robust filename sanitization: strip path components, remove all dangerous chars
    raw_name = P(file.filename or "screenshot.png").name
    # Remove path separators, null bytes, and double-dot traversal
    safe_name = re.sub(r'[^\w\s\-.]', '', raw_name).strip()
    safe_name = safe_name.replace('..', '').strip()
    if not safe_name:
        safe_name = "screenshot.png"
    allowed_ext = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    ext = P(safe_name).suffix.lower()
    if ext not in allowed_ext:
        raise HTTPException(400, f"不支持的文件类型: {ext}")
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    file_path = f"{upload_dir}/{filename}"

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "截图文件不能超过 10MB")
    with open(file_path, "wb") as f:
        f.write(content)

    screenshot = Screenshot(
        project_id=project_id,
        session_id=session_id,
        finding_id=finding_id,
        asset_id=asset_id,
        filename=filename,
        file_path=file_path,
        file_size=len(content),
        caption=caption,
        uploaded_by=request.state.user_id,
    )
    db.add(screenshot)
    await db.flush()

    if session_id:
        session = await db.get(WorkSession, session_id)
        if session:
            session.screenshots_count = (session.screenshots_count or 0) + 1
            await db.flush()

    return {"id": screenshot.id, "filename": filename, "file_path": f"/api/v1/projects/{project_id}/screenshots/{screenshot.id}/view"}


@router.get("/projects/{project_id}/screenshots")
async def list_screenshots(project_id: int, finding_id: int | None = None, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    query = select(Screenshot).where(Screenshot.project_id == project_id)
    if finding_id:
        query = query.where(Screenshot.finding_id == finding_id)
    result = await db.execute(query.order_by(Screenshot.uploaded_at.desc()))
    items = result.scalars().all()
    return {"items": [
        {"id": s.id, "filename": s.filename, "caption": s.caption,
         "finding_id": s.finding_id, "asset_id": s.asset_id,
         "file_size": s.file_size, "is_redacted": s.is_redacted,
         "view_url": f"/api/v1/projects/{project_id}/screenshots/{s.id}/view",
         "uploaded_at": s.uploaded_at.isoformat() if s.uploaded_at else None}
        for s in items
    ]}


@router.get("/projects/{project_id}/screenshots/{screenshot_id}/view")
async def view_screenshot(project_id: int, screenshot_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from fastapi.responses import FileResponse
    import mimetypes
    screenshot = await db.get(Screenshot, screenshot_id)
    if not screenshot or screenshot.project_id != project_id:
        raise HTTPException(404)
    media_type = mimetypes.guess_type(screenshot.file_path)[0] or "image/png"
    return FileResponse(screenshot.file_path, media_type=media_type)


# ─── Terminal Recordings ──────────────────────────────────

class RecordingCreate(BaseModel):
    session_id: int | None = None
    title: str = "终端录制"
    commands: list = []
    duration_seconds: int | None = None
    is_playbook: bool = False
    playbook_name: str | None = None


@router.post("/projects/{project_id}/recordings")
async def save_recording(project_id: int, req: RecordingCreate, request: Request, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    recording = TerminalRecording(
        project_id=project_id,
        session_id=req.session_id,
        title=req.title,
        commands=req.commands,
        duration_seconds=req.duration_seconds,
        recorded_by=request.state.user_id,
        is_playbook=req.is_playbook,
        playbook_name=req.playbook_name,
    )
    db.add(recording)
    await db.flush()
    return {"id": recording.id, "title": recording.title}


@router.get("/projects/{project_id}/recordings")
async def list_recordings(project_id: int, playbooks_only: bool = False, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    query = select(TerminalRecording).where(TerminalRecording.project_id == project_id)
    if playbooks_only:
        query = query.where(TerminalRecording.is_playbook == True)
    result = await db.execute(query.order_by(TerminalRecording.recorded_at.desc()))
    items = result.scalars().all()
    return {"items": [
        {"id": r.id, "title": r.title, "commands_count": len(r.commands or []),
         "duration_seconds": r.duration_seconds, "is_playbook": r.is_playbook,
         "playbook_name": r.playbook_name,
         "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None}
        for r in items
    ]}


@router.get("/playbooks")
async def list_all_playbooks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TerminalRecording).where(TerminalRecording.is_playbook == True).order_by(TerminalRecording.recorded_at.desc())
    )
    items = result.scalars().all()
    return {"items": [
        {"id": r.id, "title": r.playbook_name or r.title, "commands_count": len(r.commands or []),
         "project_id": r.project_id, "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None}
        for r in items
    ]}


# ─── Risk Acceptance ──────────────────────────────────────

class RiskAcceptRequest(BaseModel):
    client_name: str = ""
    accepted_by: str = ""
    reason: str = ""


@router.post("/projects/{project_id}/findings/{finding_id}/accept-risk")
async def accept_risk(project_id: int, finding_id: int, req: RiskAcceptRequest, request: Request, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.models.finding import Finding

    finding = await db.get(Finding, finding_id)
    if not finding or finding.project_id != project_id:
        raise HTTPException(404, "漏洞不存在")

    acceptance = RiskAcceptance(
        project_id=project_id,
        finding_id=finding_id,
        client_name=req.client_name,
        accepted_by=req.accepted_by,
        reason=req.reason,
        created_by=request.state.user_id,
    )
    db.add(acceptance)

    finding.fix_status = "accepted"
    await db.flush()
    return {"id": acceptance.id, "message": "风险已接受，漏洞状态已更新"}


@router.get("/projects/{project_id}/risk-acceptances")
async def list_risk_acceptances(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RiskAcceptance).where(RiskAcceptance.project_id == project_id).order_by(RiskAcceptance.accepted_at.desc())
    )
    items = result.scalars().all()
    return {"items": [
        {"id": a.id, "finding_id": a.finding_id, "client_name": a.client_name,
         "accepted_by": a.accepted_by, "reason": a.reason,
         "accepted_at": a.accepted_at.isoformat() if a.accepted_at else None}
        for a in items
    ]}


# ─── Project Templates ───────────────────────────────────

@router.get("/templates")
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectTemplate).order_by(ProjectTemplate.created_at.desc()))
    items = result.scalars().all()
    return {"items": [
        {"id": t.id, "name": t.name, "description": t.description,
         "mode": t.mode, "engines": t.engines,
         "created_at": t.created_at.isoformat() if t.created_at else None}
        for t in items
    ]}


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    mode: str = "combat"
    scope_rules: list = []
    engines: list = []
    pipeline_name: str | None = None
    checklist_ids: list = []
    scan_intensity: str = "standard"
    max_concurrency: int = 50


@router.post("/templates")
async def create_template(req: TemplateCreate, request: Request, db: AsyncSession = Depends(get_db)):
    template = ProjectTemplate(
        name=req.name,
        description=req.description,
        mode=req.mode,
        scope_rules=req.scope_rules,
        engines=req.engines,
        pipeline_name=req.pipeline_name,
        checklist_ids=req.checklist_ids,
        scan_intensity=req.scan_intensity,
        max_concurrency=req.max_concurrency,
        created_by=request.state.user_id,
    )
    db.add(template)
    await db.flush()
    return {"id": template.id, "name": template.name}


class TemplateFromProjectRequest(BaseModel):
    name: str | None = None
    description: str = ""


@router.post("/templates/from-project/{project_id}")
async def create_template_from_project(project_id: int, req: TemplateFromProjectRequest, request: Request, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.models.project import Project, ScopeRule

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404)

    rules_result = await db.execute(select(ScopeRule).where(ScopeRule.project_id == project_id))
    rules = [{"rule_type": r.rule_type, "target_type": r.target_type, "target_value": r.target_value, "description": r.description}
             for r in rules_result.scalars().all()]

    template = ProjectTemplate(
        name=req.name or f"{project.name} 模板",
        description=req.description,
        mode=project.mode,
        scope_rules=rules,
        scan_intensity=project.scan_intensity,
        max_concurrency=project.max_concurrency,
        created_by=request.state.user_id,
    )
    db.add(template)
    await db.flush()
    return {"id": template.id, "name": template.name}


class TemplateApplyRequest(BaseModel):
    name: str | None = None
    description: str = ""
    client_name: str = ""


@router.post("/templates/apply/{template_id}")
async def create_project_from_template(template_id: int, req: TemplateApplyRequest, request: Request, db: AsyncSession = Depends(get_db)):
    if not hasattr(request.state, 'user_id'):
        raise HTTPException(401, "请先登录")
    from backend.models.project import Project, ScopeRule

    template = await db.get(ProjectTemplate, template_id)
    if not template:
        raise HTTPException(404, "模板不存在")

    project = Project(
        name=req.name or f"新项目(基于 {template.name})",
        mode=template.mode,
        description=req.description or template.description,
        client_name=req.client_name,
        scan_intensity=template.scan_intensity,
        max_concurrency=template.max_concurrency,
        created_by=request.state.user_id,
    )
    db.add(project)
    await db.flush()

    for rule_data in (template.scope_rules or []):
        rule = ScopeRule(
            project_id=project.id,
            rule_type=rule_data.get("rule_type", "include"),
            target_type=rule_data.get("target_type", "ip"),
            target_value=rule_data.get("target_value", ""),
            description=rule_data.get("description", ""),
        )
        db.add(rule)
    await db.flush()

    return {"id": project.id, "name": project.name, "template": template.name}
