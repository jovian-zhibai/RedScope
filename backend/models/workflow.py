"""Workflow: task approval and project lifecycle management."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from backend.database import Base


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String(256), nullable=False)
    order_type = Column(String(30), nullable=False)
        # pentest_request / retest_request / emergency_response
        # baseline_check / hw_exercise / report_review
    description = Column(String(4096))
    priority = Column(String(10), default="normal")  # urgent / high / normal / low
    # Workflow status
    status = Column(String(20), default="pending")
        # pending → approved → in_progress → review → completed
        # pending → rejected
    # People
    created_by = Column(Integer, ForeignKey("users.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"))
    approved_by = Column(Integer, ForeignKey("users.id"))
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    # Extra data
    extra_data = Column(JSONB)


class WorkOrderComment(Base):
    __tablename__ = "work_order_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String(4096), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
