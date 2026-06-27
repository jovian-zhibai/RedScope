"""Workflow API: work order creation, approval, and lifecycle."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.workflow import WorkOrder, WorkOrderComment
from backend.core.rbac import require_manager

router = APIRouter()

VALID_TRANSITIONS = {
    "pending": ["approved", "rejected"],
    "approved": ["in_progress"],
    "in_progress": ["review", "completed"],
    "review": ["completed", "in_progress"],
}


class OrderCreate(BaseModel):
    title: str
    order_type: str
    description: str | None = None
    priority: str = "normal"
    project_id: int | None = None
    assigned_to: int | None = None


class StatusTransition(BaseModel):
    new_status: str
    comment: str | None = None


@router.get("")
async def list_orders(
    status: str | None = None,
    order_type: str | None = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(WorkOrder).order_by(WorkOrder.created_at.desc())
    if status:
        query = query.where(WorkOrder.status == status)
    if order_type:
        query = query.where(WorkOrder.order_type == order_type)

    if request and hasattr(request.state, 'role') and request.state.role != 'admin':
        user_id = getattr(request.state, 'user_id', 0)
        query = query.where((WorkOrder.created_by == user_id) | (WorkOrder.assigned_to == user_id))

    result = await db.execute(query)
    orders = result.scalars().all()
    return {"items": [
        {
            "id": o.id, "title": o.title, "order_type": o.order_type,
            "status": o.status, "priority": o.priority,
            "project_id": o.project_id,
            "created_by": o.created_by, "assigned_to": o.assigned_to,
            "approved_by": o.approved_by,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "approved_at": o.approved_at.isoformat() if o.approved_at else None,
            "completed_at": o.completed_at.isoformat() if o.completed_at else None,
        }
        for o in orders
    ]}


@router.post("")
async def create_order(req: OrderCreate, request: Request, db: AsyncSession = Depends(get_db)):
    order = WorkOrder(**req.model_dump(), created_by=request.state.user_id)
    db.add(order)
    await db.flush()
    return {"id": order.id, "status": "pending"}


@router.get("/{order_id}")
async def get_order(order_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    # Auth is enforced by middleware; this ensures user_id is available
    if not hasattr(request.state, 'user_id'):
        raise HTTPException(401, "请先登录")
    order = await db.get(WorkOrder, order_id)
    if not order:
        raise HTTPException(404, "工单不存在")

    comments_result = await db.execute(
        select(WorkOrderComment).where(WorkOrderComment.order_id == order_id)
        .order_by(WorkOrderComment.created_at)
    )
    comments = comments_result.scalars().all()

    from backend.models.user import User
    user_ids = list(set(c.user_id for c in comments if c.user_id))
    user_map = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map = {u.id: u.display_name or u.username for u in users_result.scalars().all()}

    return {
        "id": order.id, "title": order.title, "order_type": order.order_type,
        "description": order.description, "status": order.status,
        "priority": order.priority, "project_id": order.project_id,
        "created_by": order.created_by, "assigned_to": order.assigned_to,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "comments": [
            {"id": c.id, "user_id": c.user_id, "username": user_map.get(c.user_id, f"用户#{c.user_id}"),
             "content": c.content, "created_at": c.created_at.isoformat() if c.created_at else None}
            for c in comments
        ],
    }


@router.put("/{order_id}/transition")
async def transition_order(order_id: int, req: StatusTransition, _=Depends(require_manager), db: AsyncSession = Depends(get_db)):
    order = await db.get(WorkOrder, order_id)
    if not order:
        raise HTTPException(404, "工单不存在")

    valid_next = VALID_TRANSITIONS.get(order.status, [])
    if req.new_status not in valid_next:
        raise HTTPException(400, f"不允许从 '{order.status}' 转换到 '{req.new_status}'，允许的状态: {valid_next}")

    old_status = order.status
    order.status = req.new_status

    if req.new_status == "approved":
        order.approved_at = datetime.now()
    elif req.new_status == "in_progress":
        order.started_at = datetime.now()
    elif req.new_status == "completed":
        order.completed_at = datetime.now()

    if req.comment:
        comment = WorkOrderComment(
            order_id=order_id,
            content=f"[状态变更: {old_status} → {req.new_status}] {req.comment}",
        )
        db.add(comment)

    await db.flush()
    return {"id": order.id, "status": order.status}


class CommentCreate(BaseModel):
    content: str


@router.post("/{order_id}/comments")
async def add_comment(order_id: int, req: CommentCreate, request: Request, db: AsyncSession = Depends(get_db)):
    order = await db.get(WorkOrder, order_id)
    if not order:
        raise HTTPException(404, "工单不存在")

    comment = WorkOrderComment(
        order_id=order_id,
        user_id=request.state.user_id,
        content=req.content,
    )
    db.add(comment)
    await db.flush()
    return {"id": comment.id}
