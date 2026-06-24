from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from backend.database import Base


class VulnKnowledge(Base):
    __tablename__ = "vuln_knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cve_id = Column(String(30), index=True)
    cnvd_id = Column(String(30), index=True)
    cnnvd_id = Column(String(30))
    other_ids = Column(JSONB)
    title = Column(String(512), nullable=False)
    description = Column(String(8192))
    vuln_type = Column(String(30))
    severity = Column(String(20))
    cvss_score = Column(Numeric(3, 1))
    affected_software = Column(String(256))
    affected_vendor = Column(String(128))
    affected_versions = Column(String(512))
    fingerprints = Column(JSONB)
    weapon_stage = Column(String(20), default="disclosed")
    has_poc = Column(Boolean, default=False)
    has_exp = Column(Boolean, default=False)
    exploit_public = Column(Boolean, default=False)
    patch_available = Column(Boolean, default=False)
    patch_url = Column(String(1024))
    solution = Column(String(4096))
    references = Column(JSONB)
    tags = Column(JSONB)
    source = Column(String(30))
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    pocs = relationship("PoC", back_populates="vuln")


class PoC(Base):
    __tablename__ = "pocs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vuln_knowledge_id = Column(Integer, ForeignKey("vuln_knowledge.id"), nullable=False)
    name = Column(String(256), nullable=False)
    poc_type = Column(String(20))
    content = Column(String(65536))
    file_path = Column(String(512))
    source_url = Column(String(1024))
    verified = Column(Boolean, default=False)
    success_rate = Column(Integer)
    notes = Column(String(2048))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    vuln = relationship("VulnKnowledge", back_populates="pocs")


class FalsePositiveRecord(Base):
    __tablename__ = "false_positive_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vuln_knowledge_id = Column(Integer, ForeignKey("vuln_knowledge.id"))
    asset_fingerprint = Column(String(256))
    reason = Column(String(2048))
    reported_by = Column(Integer, ForeignKey("users.id"))
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
