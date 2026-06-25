from sqlalchemy import Column, Integer, String, Boolean, Date, Time, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from backend.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    description = Column(String(2048))
    mode = Column(String(20), nullable=False)  # combat / range / research
    status = Column(String(20), default="active")  # active / paused / completed / archived
    team_id = Column(Integer, ForeignKey("teams.id"))
    created_by = Column(Integer, ForeignKey("users.id"))
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    # Authorization (required in combat mode)
    auth_doc_path = Column(String(512))
    auth_start_date = Column(Date)
    auth_end_date = Column(Date)
    client_name = Column(String(256))
    client_contact = Column(String(256))
    emergency_contact = Column(String(256))
    # Constraints
    scan_intensity = Column(String(20), default="standard")
    max_concurrency = Column(Integer, default=50)
    time_window_start = Column(Time)
    time_window_end = Column(Time)
    sensitive_data_policy = Column(String(20), default="mask")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    creator = relationship("User", back_populates="projects_created")
    scope_rules = relationship("ScopeRule", back_populates="project", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    scan_tasks = relationship("ScanTask", back_populates="project", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="project", cascade="all, delete-orphan")


class ScopeRule(Base):
    __tablename__ = "scope_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    rule_type = Column(String(10), nullable=False)  # include / exclude
    target_type = Column(String(20), nullable=False)  # domain / ip / cidr / url / port
    target_value = Column(String(512), nullable=False)
    description = Column(String(256))
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="scope_rules")


class ScopeChangeLog(Base):
    __tablename__ = "scope_change_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    action = Column(String(20), nullable=False)
    rule_type = Column(String(10))
    target_value = Column(String(512))
    reason = Column(String(2048))
    evidence_path = Column(String(512))
    changed_by = Column(Integer, ForeignKey("users.id"))
    changed_at = Column(DateTime(timezone=True), server_default=func.now())


class AllowedTestType(Base):
    __tablename__ = "allowed_test_types"

    project_id = Column(Integer, ForeignKey("projects.id"), primary_key=True)
    test_type = Column(String(30), primary_key=True)
