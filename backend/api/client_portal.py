"""Client portal: external-facing API with strict project_id authorization."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.project import Project
from backend.models.finding import Finding
from backend.models.operational import Report
from backend.models.client import ClientAccount
from passlib.context import CryptContext
from jose import jwt, JWTError
from backend.config import get_settings

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


class ClientLogin(BaseModel):
    username: str
    password: str


class ClientAccountCreate(BaseModel):
    username: str
    password: str
    client_name: str
    project_id: int


async def _verify_client_project(request: Request, project_id: int, db=None):
    """Verify the client token's project_id matches and account is active."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "未登录")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(401, "Token无效")

    token_type = payload.get("type")
    token_project_id = payload.get("project_id")
    account_id = int(payload.get("sub", 0))

    if token_type != "client":
        raise HTTPException(403, "非客户账号无权访问客户门户")

    if token_project_id != project_id:
        raise HTTPException(403, "无权访问该项目")

    if db:
        account = await db.get(ClientAccount, account_id)
        if not account or not account.is_active:
            raise HTTPException(403, "账号已被禁用")


@router.post("/accounts")
async def create_client_account(req: ClientAccountCreate, request: Request, db: AsyncSession = Depends(get_db)):
    if not hasattr(request.state, 'role') or request.state.role not in ("admin", "leader"):
        raise HTTPException(403, "仅管理员/组长可创建客户账号")
    existing = await db.execute(select(ClientAccount).where(ClientAccount.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "客户账号已存在")

    account = ClientAccount(
        username=req.username,
        password_hash=pwd_context.hash(req.password),
        client_name=req.client_name,
        project_id=req.project_id,
    )
    db.add(account)
    await db.flush()
    return {"id": account.id, "username": account.username}


@router.post("/login")
async def client_login(req: ClientLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ClientAccount).where(ClientAccount.username == req.username))
    account = result.scalar_one_or_none()
    if not account or not pwd_context.verify(req.password, account.password_hash):
        raise HTTPException(401, "用户名或密码错误")

    from datetime import datetime, timedelta, timezone
    token = jwt.encode(
        {"sub": str(account.id), "project_id": account.project_id, "type": "client",
         "exp": datetime.now(timezone.utc) + timedelta(hours=24)},
        settings.secret_key, algorithm=settings.algorithm,
    )
    return {"access_token": token, "client_name": account.client_name, "project_id": account.project_id}


@router.get("/project/{project_id}/overview")
async def client_project_overview(project_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    await _verify_client_project(request, project_id, db)

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    severities = {}
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = await db.scalar(select(func.count()).where(Finding.project_id == project_id, Finding.severity == sev))
        severities[sev] = count

    total = sum(severities.values())
    fixed = await db.scalar(select(func.count()).where(Finding.project_id == project_id, Finding.fix_status == "fixed"))

    return {
        "project_name": project.name, "client_name": project.client_name,
        "total_findings": total, "severities": severities,
        "fixed": fixed, "unfixed": total - fixed,
        "fix_rate": round(fixed / total * 100, 1) if total > 0 else 0,
    }


@router.get("/project/{project_id}/findings")
async def client_findings(project_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    await _verify_client_project(request, project_id, db)

    result = await db.execute(
        select(Finding).where(Finding.project_id == project_id, Finding.is_false_positive == False)
        .order_by(Finding.severity)
    )
    findings = result.scalars().all()
    return {"items": [
        {"id": f.id, "title": f.title, "severity": f.severity, "vuln_type": f.vuln_type,
         "description": f.description, "solution": f.solution, "fix_status": f.fix_status,
         "cvss_score": float(f.cvss_score) if f.cvss_score else None,
         "created_at": f.created_at.isoformat() if f.created_at else None}
        for f in findings
    ]}


@router.put("/project/{project_id}/findings/{finding_id}/mark-fixed")
async def client_mark_fixed(project_id: int, finding_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    await _verify_client_project(request, project_id, db)
    finding = await db.get(Finding, finding_id)
    if not finding or finding.project_id != project_id:
        raise HTTPException(404, "漏洞不存在")
    finding.fix_status = "fixing"
    await db.flush()
    return {"status": "marked", "message": "已标记为修复中，等待安全团队复测确认"}


@router.post("/project/{project_id}/request-retest")
async def client_request_retest(project_id: int, req: dict, request: Request, db: AsyncSession = Depends(get_db)):
    await _verify_client_project(request, project_id, db)
    finding_ids = req.get("finding_ids", [])
    for fid in finding_ids:
        finding = await db.get(Finding, fid)
        if finding and finding.project_id == project_id:
            finding.fix_status = "fixing"
            finding.retest_result = "pending"
    await db.flush()
    return {"status": "requested", "message": f"已提交 {len(finding_ids)} 个漏洞的复测申请"}


@router.get("/project/{project_id}/reports")
async def client_reports(project_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    await _verify_client_project(request, project_id, db)
    result = await db.execute(select(Report).where(Report.project_id == project_id).order_by(Report.created_at.desc()))
    reports = result.scalars().all()
    return {"items": [
        {"id": r.id, "title": r.title, "report_type": r.report_type, "format": r.format,
         "generated_at": r.generated_at.isoformat() if r.generated_at else None}
        for r in reports
    ]}
