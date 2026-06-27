"""NVD/CVE vulnerability fetcher: syncs latest CVEs from NVD API."""

import httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from backend.database_sync import SyncSession
from backend.models.vuln_knowledge import VulnKnowledge

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def fetch_latest(days: int = 7, keyword: str = ""):
    params = {
        "pubStartDate": (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00.000"),
        "pubEndDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59.999"),
        "resultsPerPage": 100,
    }
    if keyword:
        params["keywordSearch"] = keyword

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(NVD_API, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"NVD fetch failed: {e}")
        return

    with SyncSession() as db:
        for item in data.get("vulnerabilities", []):
            cve_data = item.get("cve", {})
            cve_id = cve_data.get("id", "")

            existing = db.execute(select(VulnKnowledge).where(VulnKnowledge.cve_id == cve_id)).scalar_one_or_none()
            if existing:
                continue

            descriptions = cve_data.get("descriptions", [])
            desc_en = next((d["value"] for d in descriptions if d["lang"] == "en"), "")

            metrics = cve_data.get("metrics", {})
            cvss_data = metrics.get("cvssMetricV31", [{}])
            cvss_score = cvss_data[0].get("cvssData", {}).get("baseScore") if cvss_data else None
            severity = cvss_data[0].get("cvssData", {}).get("baseSeverity", "").lower() if cvss_data else "medium"

            severity_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
            severity = severity_map.get(severity, "medium")

            refs = [r.get("url", "") for r in cve_data.get("references", [])]

            vuln = VulnKnowledge(
                cve_id=cve_id,
                title=f"{cve_id}: {desc_en[:200]}",
                description=desc_en,
                severity=severity,
                cvss_score=cvss_score,
                references=refs,
                source="nvd",
                published_at=datetime.fromisoformat(cve_data.get("published", "").replace("Z", "+00:00")) if cve_data.get("published") else None,
            )
            db.add(vuln)

        db.commit()
