from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from backend.database import Base


class ScanTask(Base):
    __tablename__ = "scan_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    task_name = Column(String(256))
    scan_strategy = Column(String(20))
    engines = Column(JSONB)
    target_assets = Column(JSONB)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    started_by = Column(Integer, ForeignKey("users.id"))
    stopped_reason = Column(String(256))
    total_targets = Column(Integer, default=0)
    scanned_count = Column(Integer, default=0)
    vulns_found = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="scan_tasks")
    engine_runs = relationship("EngineRun", back_populates="scan_task")


class EngineRun(Base):
    __tablename__ = "engine_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_task_id = Column(Integer, ForeignKey("scan_tasks.id"), nullable=False)
    engine_name = Column(String(30), nullable=False)
    status = Column(String(20), default="pending")
    runner_job_id = Column(String(64))
    raw_output_path = Column(String(512))
    vulns_found = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    error_message = Column(String(4096))

    scan_task = relationship("ScanTask", back_populates="engine_runs")


class BoundaryViolation(Base):
    __tablename__ = "boundary_violations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    scan_task_id = Column(Integer, ForeignKey("scan_tasks.id"))
    target = Column(String(512))
    violation_type = Column(String(30))
    detail = Column(String(2048))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Plugin(Base):
    __tablename__ = "plugins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    description = Column(String(2048))
    category = Column(String(20))
    run_mode = Column(String(10), default="docker")
    docker_image = Column(String(256))
    dockerfile_path = Column(String(512))
    local_binary = Column(String(512))
    config_yaml = Column(String(65536))
    command_template = Column(String(1024))
    parser_path = Column(String(512))
    output_format = Column(String(20))
    is_enabled = Column(Boolean, default=True)
    is_builtin = Column(Boolean, default=False)
    health_status = Column(String(20), default="unknown")
    proxy_supported = Column(Boolean, default=False)
    proxy_flag = Column(String(256))
    installed_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScanPipeline(Base):
    __tablename__ = "scan_pipelines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    description = Column(String(2048))
    pipeline_dag = Column(JSONB, nullable=False)
    is_builtin = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
