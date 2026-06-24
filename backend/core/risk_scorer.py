"""Risk scorer: computes combined risk score based on vuln severity + asset importance + exposure."""


SEVERITY_WEIGHT = {"critical": 10.0, "high": 8.0, "medium": 5.0, "low": 2.0, "info": 0.5}
IMPORTANCE_MULTIPLIER = {"critical": 1.5, "normal": 1.0, "low": 0.6, "deprecated": 0.3}
EXPOSURE_BONUS = {"public": 1.5, "dmz": 1.2, "internal": 0.8}
WEAPON_BONUS = {"mass_exploitation": 2.0, "in_the_wild": 1.5, "exp_available": 1.3, "poc_available": 1.1, "disclosed": 1.0}


def compute_risk_score(
    severity: str,
    asset_importance: str = "normal",
    is_public: bool = False,
    weapon_stage: str = "disclosed",
    has_exploit: bool = False,
) -> float:
    base = SEVERITY_WEIGHT.get(severity, 5.0)
    importance = IMPORTANCE_MULTIPLIER.get(asset_importance, 1.0)
    exposure = 1.5 if is_public else 1.0
    weapon = WEAPON_BONUS.get(weapon_stage, 1.0)
    exploit_bonus = 1.2 if has_exploit else 1.0

    raw_score = base * importance * exposure * weapon * exploit_bonus
    return round(min(10.0, raw_score), 1)


def risk_label(score: float) -> str:
    if score >= 9.0:
        return "紧急"
    if score >= 7.0:
        return "高"
    if score >= 4.0:
        return "中"
    if score >= 2.0:
        return "低"
    return "信息"


def score_finding(finding, asset=None, vuln_knowledge=None) -> float:
    severity = finding.severity or "medium"
    importance = asset.importance if asset else "normal"
    is_public = not _is_private(asset.host) if asset and asset.host else False
    weapon = vuln_knowledge.weapon_stage if vuln_knowledge else "disclosed"
    has_exp = vuln_knowledge.has_exp if vuln_knowledge else False

    return compute_risk_score(severity, importance, is_public, weapon, has_exp)


def _is_private(host: str) -> bool:
    import ipaddress
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_private or addr.is_loopback
    except ValueError:
        return True
