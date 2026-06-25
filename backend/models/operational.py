from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from backend.database import Base


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    cred_type = Column(String(20), nullable=False)
    username = Column(String(256))
    secret_enc = Column(String(4096), nullable=False)
    domain = Column(String(128))
    source = Column(String(256))
    source_host = Column(String(256))
    related_asset_id = Column(Integer, ForeignKey("assets.id"))
    is_cracked = Column(Boolean, default=False)
    cracked_at = Column(DateTime(timezone=True))
    reuse_count = Column(Integer, default=0)
    reuse_hosts = Column(JSONB)
    found_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompromisedHost(Base):
    __tablename__ = "compromised_hosts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    hostname = Column(String(256))
    ip = Column(String(45), nullable=False)
    access_level = Column(String(20))
    shell_type = Column(String(30))
    persistence = Column(String(256))
    uploaded_files = Column(JSONB)
    modified_configs = Column(JSONB)
    entry_method = Column(String(2048))
    entry_finding_id = Column(Integer, ForeignKey("findings.id"))
    status = Column(String(20), default="active")
    attck_techniques = Column(JSONB)
    compromised_at = Column(DateTime(timezone=True), server_default=func.now())
    cleaned_at = Column(DateTime(timezone=True))


class ProxyNode(Base):
    __tablename__ = "proxy_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(128), nullable=False)
    proxy_type = Column(String(10), nullable=False)
    host = Column(String(256), nullable=False)
    port = Column(Integer, nullable=False)
    username_enc = Column(String(512))
    password_enc = Column(String(512))
    ssh_key_path = Column(String(512))
    upstream_node_id = Column(Integer, ForeignKey("proxy_nodes.id"))
    reachable_cidrs = Column(JSONB, nullable=False)
    status = Column(String(20), default="unknown")
    latency_ms = Column(Integer)
    last_check_at = Column(DateTime(timezone=True))
    tunnel_tool = Column(String(30))
    tunnel_note = Column(String(2048))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AttackTimeline(Base):
    __tablename__ = "attack_timeline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    phase = Column(String(30))
    action = Column(String(2048), nullable=False)
    target_host = Column(String(256))
    result = Column(String(20))
    attck_id = Column(String(20))
    auto_generated = Column(Boolean, default=False)
    operator_id = Column(Integer, ForeignKey("users.id"))
    related_finding_id = Column(Integer, ForeignKey("findings.id"))
    related_host_id = Column(Integer, ForeignKey("compromised_hosts.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CleanupItem(Base):
    __tablename__ = "cleanup_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    host_id = Column(Integer, ForeignKey("compromised_hosts.id"))
    item_type = Column(String(20))
    description = Column(String(2048), nullable=False)
    file_path = Column(String(512))
    is_cleaned = Column(Boolean, default=False)
    cleaned_by = Column(Integer, ForeignKey("users.id"))
    cleaned_at = Column(DateTime(timezone=True))


class Loot(Base):
    __tablename__ = "loots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    host_id = Column(Integer, ForeignKey("compromised_hosts.id"))
    loot_type = Column(String(30))
    title = Column(String(256), nullable=False)
    description = Column(String(4096))
    impact = Column(String(20))
    evidence_path = Column(String(512))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(64), nullable=False)
    target = Column(String(512))
    detail = Column(JSONB)
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(512))
    report_type = Column(String(20))
    template_id = Column(Integer)
    include_sections = Column(JSONB)
    compliance_std = Column(JSONB)
    file_path = Column(String(512))
    format = Column(String(10))
    generated_at = Column(DateTime(timezone=True))
    generated_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Checklist(Base):
    __tablename__ = "checklists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    business_type = Column(String(30))
    items = Column(JSONB, nullable=False)
    is_builtin = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChecklistResult(Base):
    __tablename__ = "checklist_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    checklist_id = Column(Integer, ForeignKey("checklists.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    item_index = Column(Integer, nullable=False)
    result = Column(String(20))  # vulnerable / not_vulnerable / not_applicable / need_retest
    finding_id = Column(Integer, ForeignKey("findings.id"))
    tester_id = Column(Integer, ForeignKey("users.id"))
    tested_at = Column(DateTime(timezone=True), server_default=func.now())


class Payload(Base):
    __tablename__ = "payloads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(64), nullable=False)
    name = Column(String(256), nullable=False)
    content = Column(String(65536), nullable=False)
    applicable_scene = Column(String(256))
    success_rate = Column(Integer)
    notes = Column(String(2048))
    owner_id = Column(Integer, ForeignKey("users.id"))
    shared_to_team = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TestNote(Base):
    __tablename__ = "test_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    content = Column(String(65536), nullable=False)
    attachments = Column(JSONB)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TaskAssignment(Base):
    __tablename__ = "task_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    module_name = Column(String(128))
    assigned_to = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default="testing")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))


class WorkSession(Base):
    __tablename__ = "work_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(256))
    status = Column(String(20), default="active")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))
    summary = Column(String(65536))
    activities = Column(JSONB, default=list)
    scans_run = Column(Integer, default=0)
    findings_added = Column(Integer, default=0)
    notes_count = Column(Integer, default=0)
    screenshots_count = Column(Integer, default=0)


class Screenshot(Base):
    __tablename__ = "screenshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("work_sessions.id"))
    finding_id = Column(Integer, ForeignKey("findings.id"))
    asset_id = Column(Integer, ForeignKey("assets.id"))
    filename = Column(String(256), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer)
    caption = Column(String(512))
    is_redacted = Column(Boolean, default=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class TerminalRecording(Base):
    __tablename__ = "terminal_recordings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("work_sessions.id"))
    title = Column(String(256))
    commands = Column(JSONB, nullable=False)
    duration_seconds = Column(Integer)
    recorded_by = Column(Integer, ForeignKey("users.id"))
    is_playbook = Column(Boolean, default=False)
    playbook_name = Column(String(256))
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class RiskAcceptance(Base):
    __tablename__ = "risk_acceptances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False)
    client_name = Column(String(256))
    accepted_by = Column(String(256))
    reason = Column(String(2048))
    accepted_at = Column(DateTime(timezone=True), server_default=func.now())
    pdf_path = Column(String(1024))
    created_by = Column(Integer, ForeignKey("users.id"))


class ProjectTemplate(Base):
    __tablename__ = "project_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    description = Column(String(2048))
    mode = Column(String(20), nullable=False)
    scope_rules = Column(JSONB, default=list)
    engines = Column(JSONB, default=list)
    pipeline_name = Column(String(256))
    checklist_ids = Column(JSONB, default=list)
    scan_intensity = Column(String(20), default="standard")
    max_concurrency = Column(Integer, default=50)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(128), primary_key=True)
    value = Column(String(4096), nullable=False, default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
