"""Dedup engine: merges duplicate findings from multiple scan engines."""

import hashlib
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.models.finding import Finding


def compute_dedup_hash(host: str, vuln_type: str, detail_hint: str = "") -> str:
    raw = f"{host}|{vuln_type}|{detail_hint}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()


def dedup_findings(db: Session, project_id: int) -> dict:
    result = db.execute(
        select(Finding).where(Finding.project_id == project_id).order_by(Finding.created_at)
    )
    findings = list(result.scalars().all())

    hash_groups: dict[str, list[Finding]] = {}
    for f in findings:
        if not f.dedup_hash:
            continue
        hash_groups.setdefault(f.dedup_hash, []).append(f)

    merged_count = 0
    for dedup_hash, group in hash_groups.items():
        if len(group) <= 1:
            continue

        primary = group[0]
        for dup in group[1:]:
            # Keep higher severity
            severity_order = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
            if severity_order.get(dup.severity, 0) > severity_order.get(primary.severity, 0):
                primary.severity = dup.severity
                primary.cvss_score = dup.cvss_score

            # Merge evidence
            if dup.evidence and primary.evidence:
                primary.evidence = {**primary.evidence, f"from_{dup.found_by}": dup.evidence}
            elif dup.evidence:
                primary.evidence = dup.evidence

            # Append engine info
            if dup.found_by and dup.found_by not in (primary.found_by or ""):
                primary.found_by = f"{primary.found_by},{dup.found_by}"

            # Mark duplicate
            dup.is_false_positive = True
            dup.description = f"[已合并到 #{primary.id}] {dup.description or ''}"
            merged_count += 1

    db.commit()
    return {"total_findings": len(findings), "duplicates_merged": merged_count}
