from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import jwt
from backend.config import get_settings
from backend.database import get_db
from backend.models.user import User

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
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
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

    user.last_login_at = datetime.utcnow()
    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
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


@router.put("/users/{user_id}")
async def admin_update_user(user_id: int, req: dict, request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role != "admin":
        raise HTTPException(403, "仅管理员可操作")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if "role" in req:
        user.role = req["role"]
    if "is_active" in req:
        user.is_active = req["is_active"]
    if "display_name" in req:
        user.display_name = req["display_name"]
    await db.flush()
    return {"message": "更新成功"}


@router.post("/projects/{project_id}/clone")
async def clone_project(project_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    from backend.models.project import Project, ScopeRule
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    new_project = Project(
        name=f"{project.name} (副本)",
        mode=project.mode,
        description=project.description,
        client_name=project.client_name,
        auth_start_date=project.auth_start_date,
        auth_end_date=project.auth_end_date,
        created_by=request.state.user_id,
    )
    db.add(new_project)
    await db.flush()

    result = await db.execute(select(ScopeRule).where(ScopeRule.project_id == project_id))
    for rule in result.scalars().all():
        new_rule = ScopeRule(
            project_id=new_project.id,
            rule_type=rule.rule_type,
            value=rule.value,
            description=rule.description,
        )
        db.add(new_rule)
    await db.flush()
    return {"id": new_project.id, "name": new_project.name}
