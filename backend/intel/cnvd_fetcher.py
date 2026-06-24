"""CNVD vulnerability fetcher: syncs Chinese national vulnerability database."""

import httpx
import re
from datetime import datetime
from sqlalchemy import select
from backend.database_sync import SyncSession
from backend.models.vuln_knowledge import VulnKnowledge

CNVD_LIST_URL = "https://www.cnvd.org.cn/flaw/list"


def fetch_latest():
    """Fetches latest CNVD vulnerabilities.
    Note: CNVD doesn't have a public API. In production, this would use
    web scraping or a third-party aggregator. This is a placeholder
    showing the data structure and integration pattern."""

    # In a real deployment, you would either:
    # 1. Scrape CNVD website (requires handling anti-bot measures)
    # 2. Use a commercial threat intel feed that includes CNVD data
    # 3. Subscribe to CNVD's paid API service
    # 4. Use community-maintained CNVD mirrors on GitHub

    sample_vulns = [
        {
            "cnvd_id": "CNVD-2025-SAMPLE1",
            "title": "泛微E-Cology SQL注入漏洞",
            "description": "泛微E-Cology OA系统存在SQL注入漏洞,攻击者可通过构造恶意请求获取数据库数据",
            "severity": "high",
            "cvss_score": 8.5,
            "affected_software": "泛微E-Cology",
            "affected_vendor": "泛微",
            "affected_versions": "<= 10.58.2",
            "fingerprints": ["ecology", "e-cology", "泛微OA", "weaver"],
            "vuln_type": "sqli",
            "weapon_stage": "poc_available",
            "has_poc": True,
            "tags": ["OA系统", "国产软件", "护网重点"],
            "source": "cnvd",
        },
    ]

    with SyncSession() as db:
        for vuln_data in sample_vulns:
            cnvd_id = vuln_data["cnvd_id"]
            existing = db.execute(
                select(VulnKnowledge).where(VulnKnowledge.cnvd_id == cnvd_id)
            ).scalar_one_or_none()
            if existing:
                continue

            vuln = VulnKnowledge(
                cnvd_id=cnvd_id,
                title=vuln_data["title"],
                description=vuln_data["description"],
                severity=vuln_data["severity"],
                cvss_score=vuln_data.get("cvss_score"),
                affected_software=vuln_data.get("affected_software"),
                affected_vendor=vuln_data.get("affected_vendor"),
                affected_versions=vuln_data.get("affected_versions"),
                fingerprints=vuln_data.get("fingerprints"),
                vuln_type=vuln_data.get("vuln_type"),
                weapon_stage=vuln_data.get("weapon_stage", "disclosed"),
                has_poc=vuln_data.get("has_poc", False),
                tags=vuln_data.get("tags"),
                source="cnvd",
                published_at=datetime.now(),
            )
            db.add(vuln)

        db.commit()


def import_from_json(json_path: str):
    """Import CNVD vulns from a JSON file (for offline/batch import)."""
    import json
    with open(json_path) as f:
        vulns = json.load(f)

    with SyncSession() as db:
        for v in vulns:
            existing = db.execute(
                select(VulnKnowledge).where(
                    (VulnKnowledge.cnvd_id == v.get("cnvd_id")) |
                    (VulnKnowledge.cve_id == v.get("cve_id"))
                )
            ).scalar_one_or_none()
            if existing:
                if v.get("cve_id") and not existing.cve_id:
                    existing.cve_id = v["cve_id"]
                continue

            vuln = VulnKnowledge(**{k: v2 for k, v2 in v.items() if hasattr(VulnKnowledge, k)})
            vuln.source = "cnvd_import"
            db.add(vuln)
        db.commit()
