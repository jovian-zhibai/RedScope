"""Dedup engine: merges duplicate findings from multiple scan engines."""

import hashlib
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.finding import Finding


def compute_dedup_hash(host: str, vuln_type: str, detail_hint: str = "") -> str:
    raw = f"{host}|{vuln_type}|{detail_hint}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()


def _merge_group(group: list[Finding]) -> int:
    severity_order = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
    primary = group[0]
    engine_set = {primary.found_by}
    merged_count = 0

    for dup in group[1:]:
        if severity_order.get(dup.severity, 0) > severity_order.get(primary.severity, 0):
            primary.severity = dup.severity
            primary.cvss_score = dup.cvss_score

        if dup.evidence and primary.evidence and isinstance(primary.evidence, dict) and isinstance(dup.evidence, dict):
            primary.evidence = {**primary.evidence, f"from_{dup.found_by}": dup.evidence}
        elif dup.evidence and not primary.evidence:
            primary.evidence = dup.evidence

        if dup.found_by:
            engine_set.add(dup.found_by)
            if dup.found_by not in (primary.found_by or ""):
                primary.found_by = f"{primary.found_by},{dup.found_by}"

        dup.fix_status = "merged"
        dup.description = f"[已合并到 #{primary.id}] {dup.description or ''}"
        merged_count += 1

    engine_count = len(engine_set)
    confidence = min(engine_count / 3.0, 1.0)
    if not primary.combined_risk_score:
        base = severity_order.get(primary.severity, 3) * 2
        primary.combined_risk_score = round(base * confidence, 1)
    if not primary.evidence:
        primary.evidence = {}
    primary.evidence["_engine_count"] = engine_count
    primary.evidence["_confidence"] = round(confidence, 2)

    return merged_count


def dedup_findings(db: Session, project_id: int) -> dict:
    result = db.execute(
        select(Finding).where(Finding.project_id == project_id, Finding.deleted_at == None).order_by(Finding.created_at)
    )
    findings = list(result.scalars().all())

    hash_groups: dict[str, list[Finding]] = {}
    for f in findings:
        if not f.dedup_hash:
            continue
        hash_groups.setdefault(f.dedup_hash, []).append(f)

    merged_count = 0
    for group in hash_groups.values():
        if len(group) > 1:
            merged_count += _merge_group(group)

    db.commit()
    return {"total_findings": len(findings), "duplicates_merged": merged_count}


async def dedup_findings_async(db: AsyncSession, project_id: int) -> dict:
    result = await db.execute(
        select(Finding).where(Finding.project_id == project_id, Finding.deleted_at == None).order_by(Finding.created_at)
    )
    findings = list(result.scalars().all())

    hash_groups: dict[str, list[Finding]] = {}
    for f in findings:
        if not f.dedup_hash:
            continue
        hash_groups.setdefault(f.dedup_hash, []).append(f)

    merged_count = 0
    for group in hash_groups.values():
        if len(group) > 1:
            merged_count += _merge_group(group)

    return {"total_findings": len(findings), "duplicates_merged": merged_count}
