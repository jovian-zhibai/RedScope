"""RBAC: Role-based access control as FastAPI dependencies."""

from fastapi import Request, HTTPException, Depends

ROLE_HIERARCHY = {"admin": 4, "manager": 3, "leader": 3, "engineer": 2, "viewer": 1}


class RequireRole:
    def __init__(self, min_role: str):
        self.min_level = ROLE_HIERARCHY.get(min_role, 0)
        self.min_role = min_role

    async def __call__(self, request: Request):
        if not hasattr(request.state, "role"):
            raise HTTPException(401, "未登录")
        user_level = ROLE_HIERARCHY.get(request.state.role, 0)
        if user_level < self.min_level:
            raise HTTPException(403, f"权限不足，需要 {self.min_role} 及以上角色")
        return request.state.role


class RequireProjectAccess:
    """Verifies the current user owns the requested project (or is admin)."""
    async def __call__(self, request: Request, project_id: int):
        user_id = getattr(request.state, "user_id", None)
        role = getattr(request.state, "role", "viewer")
        if not user_id:
            raise HTTPException(401, "未登录")

        if role == "admin":
            return user_id

        from backend.database import async_session
        from backend.models.project import Project
        async with async_session() as db:
            project = await db.get(Project, project_id)
            if not project:
                raise HTTPException(404, "项目不存在")
            if project.created_by != user_id:
                # Check tenant membership
                tenant_id = getattr(request.state, "tenant_id", None)
                if not tenant_id or project.tenant_id != tenant_id:
                    raise HTTPException(403, "无权访问该项目")
        return user_id


require_admin = RequireRole("admin")
require_manager = RequireRole("manager")
require_engineer = RequireRole("engineer")
require_viewer = RequireRole("viewer")
require_project = RequireProjectAccess()
