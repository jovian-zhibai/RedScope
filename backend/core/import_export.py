"""Import/export: handles data import from external tools and export for clients."""

import csv
import json
import io
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.models.asset import Asset
from backend.models.finding import Finding


def import_assets_from_csv(db: Session, project_id: int, csv_content: str) -> int:
    reader = csv.DictReader(io.StringIO(csv_content))
    count = 0
    for row in reader:
        host = row.get("host") or row.get("ip") or row.get("域名") or row.get("IP")
        if not host:
            continue
        port = row.get("port") or row.get("端口")
        asset = Asset(
            project_id=project_id,
            asset_type="ip" if _is_ip(host) else "domain",
            host=host.strip(),
            port=int(port) if port and port.isdigit() else None,
            application=row.get("application") or row.get("应用") or row.get("系统"),
            importance=row.get("importance") or row.get("重要性") or "normal",
            discovered_by="csv_import",
        )
        db.add(asset)
        count += 1
    db.commit()
    return count


def import_nessus_xml(db: Session, project_id: int, xml_content: str) -> int:
    import xml.etree.ElementTree as ET
    from xml.etree.ElementTree import XMLParser
    parser = XMLParser()
    root = ET.fromstring(xml_content, parser=parser)
    count = 0

    for report_host in root.findall(".//ReportHost"):
        host_name = report_host.get("name", "")
        for item in report_host.findall("ReportItem"):
            plugin_name = item.get("pluginName", "")
            severity_num = int(item.get("severity", "0"))
            severity_map = {0: "info", 1: "low", 2: "medium", 3: "high", 4: "critical"}
            severity = severity_map.get(severity_num, "info")
            port = item.get("port", "0")
            desc = item.findtext("description", "")
            solution = item.findtext("solution", "")
            cve_el = item.find("cve")
            cve_id = cve_el.text if cve_el is not None else None

            if severity_num < 1:
                continue

            finding = Finding(
                project_id=project_id,
                title=f"{plugin_name} - {host_name}:{port}"[:500],
                vuln_type="nessus_finding",
                severity=severity,
                description=desc[:4000],
                solution=solution[:4000],
                found_by="nessus_import",
            )
            db.add(finding)
            count += 1

    db.commit()
    return count


def export_findings_csv(db: Session, project_id: int) -> str:
    findings = db.execute(
        select(Finding).where(Finding.project_id == project_id).order_by(Finding.severity)
    ).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["编号", "漏洞名称", "类型", "严重程度", "CVSS", "修复状态", "描述", "修复建议", "发现方式", "发现时间"])

    for i, f in enumerate(findings, 1):
        writer.writerow([
            i, f.title, f.vuln_type, f.severity,
            float(f.cvss_score) if f.cvss_score else "",
            f.fix_status, (f.description or "")[:500],
            (f.solution or "")[:500], f.found_by,
            f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "",
        ])

    return output.getvalue()


def export_project_archive(db: Session, project_id: int) -> dict:
    from backend.models.project import Project
    project = db.get(Project, project_id)
    assets = db.execute(select(Asset).where(Asset.project_id == project_id)).scalars().all()
    findings = db.execute(select(Finding).where(Finding.project_id == project_id)).scalars().all()

    return {
        "project": {"id": project.id, "name": project.name, "mode": project.mode, "client_name": project.client_name},
        "assets": [{"host": a.host, "port": a.port, "application": a.application, "importance": a.importance} for a in assets],
        "findings": [{"title": f.title, "severity": f.severity, "vuln_type": f.vuln_type, "fix_status": f.fix_status} for f in findings],
        "exported_at": __import__("datetime").datetime.now().isoformat(),
    }


def _is_ip(s: str) -> bool:
    import ipaddress
    try:
        ipaddress.ip_address(s.strip())
        return True
    except ValueError:
        return False
