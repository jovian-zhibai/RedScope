"""Vulnerability matcher: correlates asset fingerprints with known vulnerabilities."""

import re
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from backend.models.asset import Asset
from backend.models.vuln_knowledge import VulnKnowledge


class MatchResult:
    def __init__(self, asset: Asset, vuln: VulnKnowledge, confidence: float, reason: str):
        self.asset = asset
        self.vuln = vuln
        self.confidence = confidence
        self.reason = reason


def match_asset_vulns(db: Session, asset: Asset) -> list[MatchResult]:
    if not asset.application and not asset.server and not asset.framework:
        return []

    candidates = _query_candidates(db, asset)
    results = []
    for vuln in candidates:
        confidence, reason = _calculate_match(asset, vuln)
        if confidence > 0.3:
            results.append(MatchResult(asset, vuln, confidence, reason))

    results.sort(key=lambda r: r.confidence, reverse=True)
    return results


def _query_candidates(db: Session, asset: Asset) -> list[VulnKnowledge]:
    search_terms = []
    if asset.application:
        search_terms.append(asset.application)
    if asset.server:
        search_terms.append(asset.server)
    if asset.framework:
        search_terms.append(asset.framework)

    conditions = []
    for term in search_terms:
        term_lower = term.lower().strip()
        escaped = term_lower.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(VulnKnowledge.affected_software.ilike(f"%{escaped}%"))
        conditions.append(VulnKnowledge.title.ilike(f"%{escaped}%"))

    if not conditions:
        return []

    result = db.execute(select(VulnKnowledge).where(or_(*conditions)).limit(200))
    return list(result.scalars().all())


def _calculate_match(asset: Asset, vuln: VulnKnowledge) -> tuple[float, str]:
    confidence = 0.0
    reasons = []

    # Software name match
    if asset.application and vuln.affected_software:
        if _fuzzy_match(asset.application, vuln.affected_software):
            confidence += 0.4
            reasons.append(f"软件名匹配: {asset.application}")

    # Fingerprint keyword match
    if vuln.fingerprints and isinstance(vuln.fingerprints, list):
        asset_text = f"{asset.application} {asset.server} {asset.framework}".lower()
        for fp in vuln.fingerprints:
            if fp.lower() in asset_text:
                confidence += 0.2
                reasons.append(f"指纹关键词匹配: {fp}")
                break

    # Version range match
    if asset.app_version and vuln.affected_versions:
        if _version_in_range(asset.app_version, vuln.affected_versions):
            confidence += 0.4
            reasons.append(f"版本范围匹配: {asset.app_version} ∈ {vuln.affected_versions}")
        else:
            confidence -= 0.2
            reasons.append(f"版本不在影响范围: {asset.app_version}")

    # Boost for weaponized vulns
    if vuln.weapon_stage in ("exp_available", "in_the_wild", "mass_exploitation"):
        confidence += 0.1
        reasons.append(f"高威胁: {vuln.weapon_stage}")

    confidence = max(0.0, min(1.0, confidence))
    return confidence, "; ".join(reasons)


def _fuzzy_match(app_name: str, affected: str) -> bool:
    aliases = {
        "泛微": ["ecology", "e-cology", "e-office", "e-mobile", "weaver"],
        "用友": ["yonyou", "nc", "u8", "grp-u8"],
        "致远": ["seeyon", "zhiyuan", "a6", "a8"],
        "蓝凌": ["landray", "ekp"],
        "通达": ["tongda", "office anywhere"],
        "万户": ["ezoffice", "wanhu"],
        "apache": ["httpd", "tomcat", "struts", "shiro", "dubbo", "solr", "druid"],
        "spring": ["spring boot", "spring cloud", "spring framework", "springboot"],
        "nginx": ["nginx", "openresty"],
        "thinkphp": ["thinkphp", "topthink"],
        "wordpress": ["wordpress", "wp"],
        "redis": ["redis"],
        "mysql": ["mysql", "mariadb"],
    }

    a = app_name.lower().strip()
    b = affected.lower().strip()

    if a in b or b in a:
        return True

    for canonical, alias_list in aliases.items():
        all_names = [canonical] + alias_list
        a_match = any(name in a for name in all_names)
        b_match = any(name in b for name in all_names)
        if a_match and b_match:
            return True

    return False


def _version_in_range(version: str, affected_range: str) -> bool:
    version_nums = _extract_version_nums(version)
    if not version_nums:
        return True  # Can't determine version, assume potentially affected

    affected_lower = affected_range.lower().strip()

    # Pattern: ">= X, <= Y" or ">= X and <= Y"
    range_match = re.findall(r'([><=!]+)\s*([\d.]+)', affected_lower)
    if range_match:
        for op, ver_str in range_match:
            compare_nums = _extract_version_nums(ver_str)
            if not compare_nums:
                continue
            if op in ("<=", "=<") and not (version_nums <= compare_nums):
                return False
            if op in (">=", "=>") and not (version_nums >= compare_nums):
                return False
            if op == "<" and not (version_nums < compare_nums):
                return False
            if op == ">" and not (version_nums > compare_nums):
                return False
            if op == "=" and not (version_nums == compare_nums):
                return False
        return True

    # Pattern: "before X" or "< X"
    before_match = re.search(r'before\s+([\d.]+)', affected_lower)
    if before_match:
        compare = _extract_version_nums(before_match.group(1))
        return version_nums < compare if compare else True

    # If no parseable range, be conservative
    return True


def _extract_version_nums(version: str) -> tuple:
    nums = re.findall(r'\d+', version)
    return tuple(int(n) for n in nums[:4]) if nums else ()


def batch_match_project(db: Session, project_id: int) -> list[MatchResult]:
    assets = db.execute(
        select(Asset).where(Asset.project_id == project_id, Asset.is_alive == True, Asset.deleted_at == None)
    ).scalars().all()

    all_results = []
    for asset in assets:
        matches = match_asset_vulns(db, asset)
        all_results.extend(matches)
    return all_results
