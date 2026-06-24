from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from backend.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    asset_type = Column(String(20), nullable=False)
    host = Column(String(512), nullable=False)
    port = Column(Integer)
    protocol = Column(String(10))
    url = Column(String(1024))
    # Fingerprint
    os = Column(String(128))
    server = Column(String(128))
    framework = Column(String(128))
    application = Column(String(128))
    app_version = Column(String(64))
    fingerprint_raw = Column(JSONB)
    # Status
    scope_status = Column(String(20), default="in_scope")
    importance = Column(String(20), default="normal")
    is_alive = Column(Boolean, default=True)
    discovered_by = Column(String(30))
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    auth_config = Column(JSONB)
    tags = Column(JSONB, default=list)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="assets")
    findings = relationship("Finding", back_populates="asset")
