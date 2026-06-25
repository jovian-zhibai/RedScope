"""Manual testing: checklists, payloads, test notes, and task collaboration."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.operational import Checklist, ChecklistResult, Payload, TestNote, TaskAssignment

router = APIRouter()

# ─── Built-in Checklists ──────────────────────────────────

BUILTIN_CHECKLISTS = [
    {
        "name": "电商/支付安全",
        "business_type": "ecommerce",
        "items": [
            {"title": "支付金额篡改", "category": "支付安全", "method": "拦截支付请求,修改price/amount参数为0.01", "severity": "critical"},
            {"title": "订单数量负数", "category": "支付安全", "method": "将quantity参数修改为-1或0", "severity": "high"},
            {"title": "优惠券重复使用", "category": "支付安全", "method": "使用已核销的优惠券code重新提交订单", "severity": "high"},
            {"title": "并发下单竞态条件", "category": "支付安全", "method": "使用多线程同时提交相同优惠券的订单", "severity": "high"},
            {"title": "越权查看他人订单", "category": "越权", "method": "遍历orderId查看其他用户订单详情", "severity": "high"},
            {"title": "订单状态跳过", "category": "逻辑", "method": "直接调用确认收货接口跳过支付步骤", "severity": "critical"},
        ],
    },
    {
        "name": "用户认证系统",
        "business_type": "user_system",
        "items": [
            {"title": "密码重置token可预测", "category": "认证", "method": "多次请求密码重置,分析token规律", "severity": "critical"},
            {"title": "短信验证码可爆破", "category": "认证", "method": "使用4-6位纯数字字典爆破验证码", "severity": "high"},
            {"title": "登录无次数限制", "category": "认证", "method": "对同一账号连续登录失败超过20次观察是否锁定", "severity": "medium"},
            {"title": "水平越权", "category": "越权", "method": "修改请求中的userId参数查看他人信息", "severity": "high"},
            {"title": "垂直越权", "category": "越权", "method": "普通用户token访问/admin/接口", "severity": "critical"},
            {"title": "任意用户注册", "category": "认证", "method": "绕过邀请码/审核机制直接注册", "severity": "medium"},
            {"title": "密码明文传输", "category": "配置", "method": "抓包检查登录请求中密码是否加密", "severity": "medium"},
            {"title": "会话固定", "category": "会话", "method": "登录前后SessionID是否变化", "severity": "medium"},
        ],
    },
    {
        "name": "文件操作安全",
        "business_type": "file_ops",
        "items": [
            {"title": "文件上传-后缀绕过", "category": "上传", "method": "双写后缀(.pphphp)、大小写(.PhP)、特殊字符(.php::$DATA)", "severity": "critical"},
            {"title": "文件上传-Content-Type绕过", "category": "上传", "method": "修改Content-Type为image/jpeg但保持php后缀", "severity": "critical"},
            {"title": "文件上传-图片马", "category": "上传", "method": "在图片文件末尾追加PHP代码", "severity": "high"},
            {"title": "目录穿越", "category": "下载", "method": "filename参数使用../../../etc/passwd", "severity": "critical"},
            {"title": "任意文件下载", "category": "下载", "method": "修改文件路径参数读取服务端任意文件", "severity": "high"},
            {"title": "任意文件删除", "category": "文件", "method": "删除接口修改文件路径参数", "severity": "critical"},
        ],
    },
    {
        "name": "API接口安全",
        "business_type": "api",
        "items": [
            {"title": "未授权访问", "category": "认证", "method": "不带Token直接访问各接口", "severity": "high"},
            {"title": "批量数据获取(BOLA)", "category": "越权", "method": "遍历资源ID获取他人数据", "severity": "high"},
            {"title": "批量操作无限制", "category": "限速", "method": "高频调用接口检查是否有速率限制", "severity": "medium"},
            {"title": "GraphQL内省", "category": "信息泄露", "method": "发送{__schema{types{name}}}查询", "severity": "medium"},
            {"title": "参数污染", "category": "注入", "method": "同一参数传递多个值观察行为", "severity": "medium"},
            {"title": "请求方法绕过", "category": "认证", "method": "用PUT/PATCH/DELETE替代受限的GET/POST", "severity": "medium"},
        ],
    },
]


@router.get("/checklists")
async def list_checklists(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Checklist).order_by(Checklist.created_at))
    items = result.scalars().all()
    return {"items": [
        {"id": c.id, "name": c.name, "business_type": c.business_type,
         "item_count": len(c.items) if c.items else 0, "is_builtin": c.is_builtin}
        for c in items
    ], "builtin_available": [c["name"] for c in BUILTIN_CHECKLISTS]}


@router.post("/checklists/init-builtin")
async def init_builtin_checklists(request: Request, db: AsyncSession = Depends(get_db)):
    if request.state.role not in ("admin", "leader"):
        raise HTTPException(403, "仅管理员/组长可初始化")
    count = 0
    for cl in BUILTIN_CHECKLISTS:
        existing = await db.execute(select(Checklist).where(Checklist.name == cl["name"]))
        if existing.scalar_one_or_none():
            continue
        checklist = Checklist(name=cl["name"], business_type=cl["business_type"], items=cl["items"], is_builtin=True)
        db.add(checklist)
        count += 1
    await db.flush()
    return {"initialized": count}


@router.get("/checklists/{checklist_id}")
async def get_checklist(checklist_id: int, db: AsyncSession = Depends(get_db)):
    cl = await db.get(Checklist, checklist_id)
    if not cl:
        raise HTTPException(404, "Checklist不存在")
    return {"id": cl.id, "name": cl.name, "business_type": cl.business_type, "items": cl.items, "is_builtin": cl.is_builtin}


@router.post("/checklists/{checklist_id}/results")
async def save_checklist_result(
    checklist_id: int, project_id: int, req: dict, _=Depends(require_project), db: AsyncSession = Depends(get_db)
):
    result = ChecklistResult(
        project_id=project_id,
        checklist_id=checklist_id,
        asset_id=req.get("asset_id"),
        item_index=req["item_index"],
        result=req["result"],
        finding_id=req.get("finding_id"),
    )
    db.add(result)
    await db.flush()
    return {"id": result.id}


@router.get("/checklists/{checklist_id}/results")
async def get_checklist_results(checklist_id: int, project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChecklistResult).where(
            ChecklistResult.checklist_id == checklist_id,
            ChecklistResult.project_id == project_id,
        )
    )
    items = result.scalars().all()
    return {"items": [
        {"id": r.id, "item_index": r.item_index, "result": r.result, "finding_id": r.finding_id}
        for r in items
    ]}


# ─── Payloads ─────────────────────────────────────────────

class PayloadCreate(BaseModel):
    category: str
    name: str
    content: str
    applicable_scene: str | None = None
    notes: str | None = None
    shared_to_team: bool = False


@router.get("/payloads")
async def list_payloads(category: str | None = None, request: Request = None, db: AsyncSession = Depends(get_db)):
    query = select(Payload).order_by(Payload.category, Payload.created_at)
    if category:
        query = query.where(Payload.category == category)
    if request and hasattr(request.state, 'user_id'):
        user_id = request.state.user_id
        query = query.where((Payload.shared_to_team == True) | (Payload.owner_id == user_id))
    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": [
        {"id": p.id, "category": p.category, "name": p.name,
         "content": p.content, "applicable_scene": p.applicable_scene,
         "success_rate": p.success_rate, "shared_to_team": p.shared_to_team}
        for p in items
    ]}


@router.post("/payloads")
async def create_payload(req: PayloadCreate, request: Request, db: AsyncSession = Depends(get_db)):
    payload = Payload(**req.model_dump(), owner_id=request.state.user_id)
    db.add(payload)
    await db.flush()
    return {"id": payload.id}


@router.delete("/payloads/{payload_id}")
async def delete_payload(payload_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    payload = await db.get(Payload, payload_id)
    if not payload:
        raise HTTPException(404, "Payload不存在")
    if payload.owner_id and payload.owner_id != request.state.user_id and request.state.role != "admin":
        raise HTTPException(403, "只能删除自己的 Payload")
    await db.delete(payload)
    await db.flush()
    return {"status": "deleted"}


# ─── Test Notes ───────────────────────────────────────────

@router.get("/notes")
async def list_notes(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TestNote).where(TestNote.project_id == project_id).order_by(TestNote.created_at.desc())
    )
    items = result.scalars().all()
    return {"items": [
        {"id": n.id, "content": n.content, "asset_id": n.asset_id,
         "attachments": n.attachments, "created_at": n.created_at.isoformat() if n.created_at else None}
        for n in items
    ]}


@router.post("/notes")
async def create_note(project_id: int, req: dict, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    note = TestNote(
        project_id=project_id,
        asset_id=req.get("asset_id"),
        content=req["content"],
        attachments=req.get("attachments"),
    )
    db.add(note)
    await db.flush()
    return {"id": note.id}


# ─── Task Assignments (Anti-collision) ────────────────────

@router.get("/assignments")
async def list_assignments(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TaskAssignment).where(TaskAssignment.project_id == project_id)
    )
    items = result.scalars().all()
    return {"items": [
        {"id": a.id, "module_name": a.module_name, "assigned_to": a.assigned_to,
         "asset_id": a.asset_id, "status": a.status,
         "started_at": a.started_at.isoformat() if a.started_at else None}
        for a in items
    ]}


@router.post("/assignments")
async def create_assignment(project_id: int, req: dict, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    assignment = TaskAssignment(
        project_id=project_id,
        asset_id=req.get("asset_id"),
        module_name=req.get("module_name"),
        assigned_to=req.get("assigned_to"),
    )
    db.add(assignment)
    await db.flush()
    return {"id": assignment.id}


@router.put("/assignments/{assignment_id}/complete")
async def complete_assignment(assignment_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    a = await db.get(TaskAssignment, assignment_id)
    if not a:
        raise HTTPException(404, "任务不存在")
    if a.assigned_to and a.assigned_to != request.state.user_id and request.state.role != "admin":
        raise HTTPException(403, "只能完成分配给自己的任务")
    a.status = "completed"
    a.completed_at = datetime.now()
    await db.flush()
    return {"status": "completed"}
