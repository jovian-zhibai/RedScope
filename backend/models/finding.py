from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from backend.database import Base


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    vuln_knowledge_id = Column(Integer, ForeignKey("vuln_knowledge.id"))
    title = Column(String(512), nullable=False)
    vuln_type = Column(String(30))
    severity = Column(String(20))
    cvss_score = Column(Numeric(3, 1))
    description = Column(String(4096))
    detail = Column(String(8192))
    solution = Column(String(4096))
    found_by = Column(String(30))
    is_verified = Column(Boolean, default=False)
    is_false_positive = Column(Boolean, default=False)
    business_impact = Column(String(20))
    combined_risk_score = Column(Numeric(3, 1))
    evidence = Column(JSONB)
    fix_status = Column(String(20), default="unfixed")
    fixed_at = Column(DateTime(timezone=True))
    retest_result = Column(String(20))
    retested_at = Column(DateTime(timezone=True))
    dedup_hash = Column(String(64), index=True)
    found_by_user = Column(Integer, ForeignKey("users.id"))
    attck_techniques = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="findings")
    asset = relationship("Asset", back_populates="findings")


class AttackChain(Base):
    __tablename__ = "attack_chains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    chain_name = Column(String(256))
    description = Column(String(4096))
    combined_severity = Column(String(20))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    steps = relationship("AttackChainStep", back_populates="chain", order_by="AttackChainStep.step_order")


class AttackChainStep(Base):
    __tablename__ = "attack_chain_steps"

    chain_id = Column(Integer, ForeignKey("attack_chains.id"), primary_key=True)
    step_order = Column(Integer, primary_key=True)
    finding_id = Column(Integer, ForeignKey("findings.id"))
    description = Column(String(2048))

    chain = relationship("AttackChain", back_populates="steps")
