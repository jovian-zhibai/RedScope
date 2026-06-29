from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import jwt
from backend.config import get_settings
from backend.database import get_db
from backend.models.user import User
from backend.models.tenant import TenantUser

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    email: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


async def _get_user_tenant_id(db, user_id: int) -> int | None:
    result = await db.execute(select(TenantUser).where(TenantUser.user_id == user_id))
    tu = result.scalar_one_or_none()
    return tu.tenant_id if tu else None


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if not settings.allow_public_registration:
        raise HTTPException(403, "注册已关闭，请联系管理员创建账号")
    if len(req.password) < 8:
        raise HTTPException(400, "密码长度不能少于8位")
    if req.password.isdigit() or req.password.isalpha():
        raise HTTPException(400, "密码必须包含字母和数字")
    if len(req.username) < 3:
        raise HTTPException(400, "用户名长度不能少于3位")

    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "用户名已存在")

    user = User(
        username=req.username,
        password_hash=pwd_context.hash(req.password),
        display_name=req.display_name or req.username,
        email=req.email,
    )
    db.add(user)
    await db.flush()

    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role},
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")

    if not user.is_active:
        raise HTTPException(403, "账号已被禁用")

    user.last_login_at = datetime.now(timezone.utc)
    tenant_id = await _get_user_tenant_id(db, user.id)
    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role, "tenant_id": tenant_id})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role},
    )


@router.get("/me")
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, request.state.user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    return {
        "id": user.id, "username": user.username, "display_name": user.display_name,
        "role": user.role, "email": user.email, "phone": user.phone,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.put("/me")
async def update_profile(req: UpdateProfileRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, request.state.user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if req.display_name is not None:
        user.display_name = req.display_name
    if req.email is not None:
        user.email = req.email
    if req.phone is not None:
        user.phone = req.phone
    await db.flush()
    return {"message": "更新成功"}


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, request.state.user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if not pwd_context.verify(req.old_password, user.password_hash):
        raise HTTPException(400, "原密码错误")
    if len(req.new_password) < 8:
        raise HTTPException(400, "新密码长度不能少于8位")
    if req.new_password.isdigit() or req.new_password.isalpha():
        raise HTTPException(400, "新密码必须包含字母和数字")
    user.password_hash = pwd_context.hash(req.new_password)
    await db.flush()
    return {"message": "密码修改成功"}


class AdminCreateUserRequest(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    role: str = "engineer"


@router.post("/users")
async def admin_create_user(req: AdminCreateUserRequest, request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role != "admin":
        raise HTTPException(403, "仅管理员可创建用户")
    if len(req.password) < 8:
        raise HTTPException(400, "密码长度不能少于8位")
    if len(req.username) < 3:
        raise HTTPException(400, "用户名长度不能少于3位")

    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "用户名已存在")

    allowed_roles = {"admin", "manager", "leader", "engineer", "viewer"}
    if req.role not in allowed_roles:
        raise HTTPException(400, f"无效角色，允许: {', '.join(allowed_roles)}")

    user = User(
        username=req.username,
        password_hash=pwd_context.hash(req.password),
        display_name=req.display_name or req.username,
        role=req.role,
    )
    db.add(user)
    await db.flush()
    return {"id": user.id, "username": user.username, "role": user.role, "message": "用户已创建"}


@router.get("/users")
async def list_users(request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role != "admin":
        raise HTTPException(403, "仅管理员可操作")
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return {"items": [
        {"id": u.id, "username": u.username, "display_name": u.display_name,
         "role": u.role, "email": u.email, "is_active": u.is_active,
         "created_at": u.created_at.isoformat() if u.created_at else None,
         "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None}
        for u in users
    ]}


class AdminUpdateUserRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    display_name: str | None = None


@router.put("/users/{user_id}")
async def admin_update_user(user_id: int, req: AdminUpdateUserRequest, request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role != "admin":
        raise HTTPException(403, "仅管理员可操作")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if req.role is not None:
        allowed_roles = {"admin", "manager", "leader", "engineer", "viewer"}
        if req.role not in allowed_roles:
            raise HTTPException(400, f"无效角色，允许: {', '.join(allowed_roles)}")
        if user.role == "admin" and req.role != "admin":
            admin_count = await db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.is_active == True))
            if admin_count <= 1:
                raise HTTPException(400, "至少需要保留一个活跃管理员，不能降权最后一位管理员")
        user.role = req.role
    if req.is_active is not None:
        if not req.is_active and user.role == "admin":
            admin_count = await db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.is_active == True))
            if admin_count <= 1:
                raise HTTPException(400, "不能禁用最后一位管理员")
        user.is_active = req.is_active
    if req.display_name is not None:
        user.display_name = req.display_name
    await db.flush()
    return {"message": "更新成功"}


@router.get("/settings/system")
async def get_system_settings(request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role != "admin":
        raise HTTPException(403, "仅管理员可查看系统配置")
    s = get_settings()
    from backend.models.operational import SystemSetting
    result = await db.execute(select(SystemSetting))
    db_settings = {r.key: r.value for r in result.scalars().all()}

    return {
        "llm_api_key": "****" + s.llm_api_key[-4:] if s.llm_api_key and len(s.llm_api_key) > 8 else ("已配置" if s.llm_api_key else ""),
        "llm_base_url": db_settings.get("llm_base_url", s.llm_base_url),
        "llm_model": db_settings.get("llm_model", s.llm_model),
        "cors_origins": s.cors_origins,
        "notify_webhook_url": db_settings.get("notify_webhook_url", s.notify_webhook_url),
        "notify_channel": db_settings.get("notify_channel", s.notify_channel),
        "max_concurrent_scans": s.max_concurrent_scans,
        "max_targets_per_scan": s.max_targets_per_scan,
        "environment": s.environment,
    }


class SystemSettingsUpdate(BaseModel):
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    notify_webhook_url: str | None = None
    notify_channel: str | None = None
    max_concurrent_scans: int | None = None
    max_targets_per_scan: int | None = None
    nvd_api_key: str | None = None


@router.put("/settings/system")
async def update_system_settings(req: SystemSettingsUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role != "admin":
        raise HTTPException(403, "仅管理员可修改")
    from backend.models.operational import SystemSetting

    allowed_keys = {"llm_api_key", "llm_base_url", "llm_model", "notify_webhook_url", "notify_channel",
                     "max_concurrent_scans", "max_targets_per_scan", "nvd_api_key"}
    VALID_CHANNELS = {"wecom", "dingtalk", "feishu", "slack", "telegram"}
    req_dict = {k: v for k, v in req.model_dump().items() if v is not None}
    for key, value in req_dict.items():
        if key not in allowed_keys:
            continue
        if key == "notify_channel" and value not in VALID_CHANNELS:
            raise HTTPException(400, f"无效的通知渠道: {value}")
        if key in ("max_concurrent_scans", "max_targets_per_scan"):
            try:
                int_val = int(value)
                if int_val < 1 or int_val > 10000:
                    raise HTTPException(400, f"{key} 范围 1-10000")
            except (ValueError, TypeError):
                raise HTTPException(400, f"{key} 必须是整数")
        existing = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = existing.scalar_one_or_none()
        if setting:
            setting.value = str(value)
        else:
            db.add(SystemSetting(key=key, value=str(value)))
    await db.flush()
    return {"message": "配置已保存"}


@router.post("/settings/test-llm")
async def test_llm_connection(request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role != "admin":
        raise HTTPException(403, "仅管理员可操作")
    from backend.models.operational import SystemSetting

    result = await db.execute(select(SystemSetting))
    db_settings = {r.key: r.value for r in result.scalars().all()}

    api_key = db_settings.get("llm_api_key", get_settings().llm_api_key)
    base_url = db_settings.get("llm_base_url", get_settings().llm_base_url)
    model = db_settings.get("llm_model", get_settings().llm_model)

    if not api_key:
        return {"status": "failed", "error": "API Key 未配置"}

    try:
        from backend.ai.llm_client import LLMClient
        client = LLMClient(api_key=api_key, base_url=base_url, model=model)
        reply = await client.chat("你好", "回复'连接成功'四个字即可", temperature=0)
        return {"status": "ok", "reply": reply[:100]}
    except Exception as e:
        return {"status": "failed", "error": "连接失败，请检查 API Key 和地址是否正确"}


@router.get("/audit-logs")
async def get_audit_logs(request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role != "admin":
        raise HTTPException(403, "仅管理员可查看")
    from backend.models.operational import AuditLog
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)
    )
    logs = result.scalars().all()
    return {"items": [
        {"id": l.id, "user_id": l.user_id, "action": l.action,
         "target_type": l.target, "detail": l.detail,
         "ip_address": l.ip_address, "severity": (l.detail or {}).get("severity", "info"),
         "created_at": l.created_at.isoformat() if l.created_at else None}
        for l in logs
    ]}


@router.post("/projects/{project_id}/clone")
async def clone_project(project_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    from backend.models.project import Project, ScopeRule
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    # Verify user has access to the source project
    user_id = request.state.user_id
    role = getattr(request.state, 'role', 'viewer')
    tenant_id = getattr(request.state, 'tenant_id', None)
    if role != 'admin':
        if project.created_by != user_id:
            if tenant_id and project.tenant_id != tenant_id:
                raise HTTPException(403, "无权复制该项目")
            elif not tenant_id:
                raise HTTPException(403, "无权复制该项目")

    new_project = Project(
        name=f"{project.name} (副本)",
        mode=project.mode,
        description=project.description,
        client_name=project.client_name,
        auth_start_date=project.auth_start_date,
        auth_end_date=project.auth_end_date,
        created_by=request.state.user_id,
        tenant_id=getattr(request.state, 'tenant_id', project.tenant_id),
    )
    db.add(new_project)
    await db.flush()

    result = await db.execute(select(ScopeRule).where(ScopeRule.project_id == project_id))
    for rule in result.scalars().all():
        new_rule = ScopeRule(
            project_id=new_project.id,
            rule_type=rule.rule_type,
            target_type=rule.target_type,
            target_value=rule.target_value,
            description=rule.description,
        )
        db.add(new_rule)
    await db.flush()
    return {"id": new_project.id, "name": new_project.name}
