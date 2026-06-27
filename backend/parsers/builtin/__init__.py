"""Built-in parsers: convert raw tool output to standardized findings."""

import hashlib
import json
import logging
from pathlib import Path

try:
    import defusedxml.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

logger = logging.getLogger("parsers")


def _safe_parse_xml(file_path: str):
    tree = ET.parse(file_path)
    return tree

def _safe_fromstring(xml_text: str):
    return ET.fromstring(xml_text)


def parse_output(engine_name: str, output_format: str, output_dir: str, output_path: str) -> list[dict]:
    parsers = {
        "nmap": parse_nmap,
        "nuclei": parse_nuclei,
        "subfinder": parse_subfinder,
        "httpx": parse_httpx,
        "sqlmap": parse_sqlmap,
        "dirsearch": parse_dirsearch,
        "afrog": parse_afrog,
        "fscan": parse_fscan,
    }
    parser = parsers.get(engine_name)
    if not parser:
        return parse_generic(output_dir, output_path, output_format)

    full_path = str(Path(output_dir) / Path(output_path).name) if not Path(output_path).is_absolute() else output_path.replace("/output", output_dir)

    p = Path(full_path)
    if not p.exists():
        logger.warning(f"[{engine_name}] Output file not found: {full_path}")
        all_files = list(Path(output_dir).rglob("*")) if Path(output_dir).exists() else []
        logger.warning(f"[{engine_name}] Files in output_dir: {[str(f) for f in all_files[:20]]}")
        return []

    logger.info(f"[{engine_name}] Parsing output: {full_path} ({p.stat().st_size} bytes)")
    return parser(full_path, output_dir)


def _dedup_hash(*args) -> str:
    return hashlib.md5("|".join(str(a) for a in args).encode()).hexdigest()


def parse_nmap(file_path: str, output_dir: str) -> list[dict]:
    results = []
    try:
        tree = _safe_parse_xml(file_path)
        root = tree.getroot()
        for host in root.findall(".//host"):
            addr_el = host.find("address")
            if addr_el is None:
                continue
            addr = addr_el.get("addr", "")
            for port in host.findall(".//port"):
                state = port.find("state")
                if state is None or state.get("state") != "open":
                    continue
                portid = port.get("portid", "")
                protocol = port.get("protocol", "tcp")
                service = port.find("service")
                svc_name = service.get("name", "") if service is not None else ""
                svc_product = service.get("product", "") if service is not None else ""
                svc_version = service.get("version", "") if service is not None else ""
                results.append({
                    "type": "asset",
                    "host": addr,
                    "port": int(portid),
                    "protocol": protocol,
                    "service": svc_name,
                    "product": svc_product,
                    "version": svc_version,
                    "title": f"{addr}:{portid} - {svc_name} {svc_product}",
                    "severity": "info",
                    "dedup_hash": _dedup_hash("nmap", addr, portid),
                })
    except Exception as e:
        logger.error(f"[nmap] Parse failed for {file_path}: {e}", exc_info=True)
    return results


def parse_nuclei(file_path: str, output_dir: str) -> list[dict]:
    results = []
    try:
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue

                host = item.get("host", item.get("matched-at", ""))
                template_id = item.get("template-id", "")
                info = item.get("info", {})
                severity = info.get("severity", "info").lower()
                name = info.get("name", template_id)
                desc = info.get("description", "")
                tags = info.get("tags", [])
                reference = info.get("reference", [])
                matcher_name = item.get("matcher-name", "")
                classification = info.get("classification", {})
                cvss_score = classification.get("cvss-score") or classification.get("cvss_score")
                cve = ""
                for tag in (tags if isinstance(tags, list) else tags.split(",")):
                    if tag.upper().startswith("CVE-"):
                        cve = tag.upper()
                        break
                if not cve and classification.get("cve-id"):
                    cve_ids = classification["cve-id"]
                    if isinstance(cve_ids, list) and cve_ids:
                        cve = cve_ids[0].upper()
                    elif isinstance(cve_ids, str):
                        cve = cve_ids.upper()

                results.append({
                    "title": f"{name} - {host}",
                    "vuln_type": _guess_vuln_type(tags, name),
                    "severity": severity,
                    "cvss_score": float(cvss_score) if cvss_score else None,
                    "description": desc,
                    "detail": f"Template: {template_id}\nMatcher: {matcher_name}\nHost: {host}\nCVE: {cve}" if cve else f"Template: {template_id}\nMatcher: {matcher_name}\nHost: {host}",
                    "solution": "\n".join(reference) if isinstance(reference, list) else str(reference),
                    "evidence": {
                        "request": item.get("request", ""),
                        "response": item.get("response", "")[:2000],
                        "curl_command": item.get("curl-command", ""),
                    },
                    "host": host,
                    "matched_cve": cve,
                    "dedup_hash": _dedup_hash("nuclei", host, template_id),
                })
    except Exception as e:
        logger.error(f"[nuclei] Parse failed for {file_path}: {e}", exc_info=True)
    return results


def parse_subfinder(file_path: str, output_dir: str) -> list[dict]:
    results = []
    try:
        with open(file_path) as f:
            for line in f:
                domain = line.strip()
                if domain:
                    results.append({
                        "type": "asset",
                        "host": domain,
                        "asset_type": "subdomain",
                        "title": f"子域名发现: {domain}",
                        "severity": "info",
                        "dedup_hash": _dedup_hash("subfinder", domain),
                    })
    except Exception as e:
        logger.error(f"[subfinder] Parse failed for {file_path}: {e}", exc_info=True)
    return results


def parse_httpx(file_path: str, output_dir: str) -> list[dict]:
    results = []
    try:
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue

                url = item.get("url", item.get("input", ""))
                status = item.get("status_code", 0)
                title = item.get("title", "")
                tech = item.get("tech", [])
                webserver = item.get("webserver", "")
                host = item.get("host", url)

                results.append({
                    "type": "asset",
                    "host": host,
                    "url": url,
                    "status_code": status,
                    "title": f"{url} [{status}] {title}",
                    "server": webserver,
                    "tech_stack": tech,
                    "severity": "info",
                    "dedup_hash": _dedup_hash("httpx", url),
                })
    except Exception as e:
        logger.error(f"[httpx] Parse failed for {file_path}: {e}", exc_info=True)
    return results


def parse_sqlmap(file_path: str, output_dir: str) -> list[dict]:
    results = []
    target_dir = Path(output_dir)
    try:
        for log_file in target_dir.rglob("log"):
            content = log_file.read_text(errors="replace")
            if "is vulnerable" in content.lower() or "injectable" in content.lower():
                parts = str(log_file.parent.name)
                results.append({
                    "title": f"SQL注入漏洞 - {parts}",
                    "vuln_type": "sqli",
                    "severity": "high",
                    "description": "SQLMap检测到SQL注入漏洞",
                    "detail": content[:4000],
                    "solution": "使用参数化查询,对用户输入进行严格过滤和转义",
                    "evidence": {"raw_log": content[:2000]},
                    "dedup_hash": _dedup_hash("sqlmap", parts),
                })
    except Exception as e:
        logger.error(f"[sqlmap] Parse failed for {file_path}: {e}", exc_info=True)
    return results


def parse_dirsearch(file_path: str, output_dir: str) -> list[dict]:
    results = []
    try:
        with open(file_path) as f:
            data = json.load(f)

        entries = data if isinstance(data, list) else data.get("results", [])
        for item in entries:
            url = item.get("url", "")
            status = item.get("status", 0)
            if status in (200, 301, 302, 403):
                severity = "info"
                title = f"目录发现: {url} [{status}]"
                path = item.get("path", url)
                sensitive_patterns = [".git", ".env", ".bak", "backup", "admin", "config",
                                      "phpinfo", ".sql", ".log", "wp-admin", ".svn"]
                for pat in sensitive_patterns:
                    if pat in path.lower():
                        severity = "medium"
                        title = f"敏感文件发现: {url} [{status}]"
                        break

                results.append({
                    "title": title,
                    "vuln_type": "info_leak" if severity != "info" else "directory",
                    "severity": severity,
                    "description": f"发现路径 {path}, HTTP状态码 {status}",
                    "host": url,
                    "dedup_hash": _dedup_hash("dirsearch", url),
                })
    except Exception as e:
        logger.error(f"[dirsearch] Parse failed for {file_path}: {e}", exc_info=True)
    return results


def parse_generic(output_dir: str, output_path: str, fmt: str) -> list[dict]:
    full = Path(output_dir) / Path(output_path).name
    if not full.exists():
        return []
    content = full.read_text(errors="replace")
    return [{"title": f"Raw output from {output_path}", "detail": content[:4000], "severity": "info"}]


def _guess_vuln_type(tags, name: str) -> str:
    name_lower = name.lower()
    tag_str = ",".join(tags) if isinstance(tags, list) else str(tags)
    combined = f"{name_lower} {tag_str}".lower()
    mapping = {
        "sqli": ["sqli", "sql-injection", "sql injection"],
        "xss": ["xss", "cross-site scripting"],
        "rce": ["rce", "remote-code-execution", "command-injection"],
        "ssrf": ["ssrf", "server-side request"],
        "lfi": ["lfi", "local-file-inclusion", "file-inclusion"],
        "file_upload": ["file-upload", "upload"],
        "xxe": ["xxe", "xml-external"],
        "auth_bypass": ["auth-bypass", "authentication-bypass", "unauth"],
        "info_leak": ["info-disclosure", "information-disclosure", "exposure", "config"],
        "deserialization": ["deserialization", "deserialize"],
    }
    for vuln_type, keywords in mapping.items():
        if any(kw in combined for kw in keywords):
            return vuln_type
    return "other"


def parse_afrog(file_path: str, output_dir: str) -> list[dict]:
    """Parse afrog JSON output — similar to nuclei but different field names."""
    results = []
    try:
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue

                url = item.get("target", item.get("url", ""))
                poc_id = item.get("pocId", item.get("poc_id", ""))
                severity = item.get("severity", "info").lower()
                vuln_name = item.get("vulName", item.get("name", poc_id))
                result_status = item.get("result", "")

                if result_status in ("failed", "false"):
                    continue

                results.append({
                    "title": f"{vuln_name} - {url}",
                    "vuln_type": _guess_vuln_type([], vuln_name),
                    "severity": severity,
                    "description": f"PoC: {poc_id}",
                    "detail": f"Target: {url}\nPoC ID: {poc_id}\nResult: {result_status}",
                    "host": url,
                    "dedup_hash": _dedup_hash("afrog", url, poc_id),
                })
    except Exception as e:
        logger.error(f"[afrog] Parse failed for {file_path}: {e}", exc_info=True)
    return results


def parse_fscan(file_path: str, output_dir: str) -> list[dict]:
    """Parse fscan text output — line-based mixed asset/vuln results."""
    results = []
    result_file = Path(output_dir) / "result.txt"
    if not result_file.exists():
        result_file = Path(file_path)
    if not result_file.exists():
        return []

    try:
        content = result_file.read_text(errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue

            if "[+]" in line and ("open" in line.lower() or "alive" in line.lower()):
                parts = line.split()
                for p in parts:
                    if ":" in p and not p.startswith("["):
                        host_port = p.split(":")
                        if len(host_port) == 2:
                            try:
                                port = int(host_port[1])
                                results.append({
                                    "type": "asset",
                                    "host": host_port[0],
                                    "port": port,
                                    "asset_type": "ip",
                                    "title": f"{host_port[0]}:{port} open",
                                    "severity": "info",
                                    "dedup_hash": _dedup_hash("fscan", host_port[0], str(port)),
                                })
                            except ValueError:
                                pass

            elif any(tag in line for tag in ["[+]", "[*]", "vuln", "MS17", "CVE", "poc"]):
                if "open" not in line.lower() and "alive" not in line.lower():
                    severity = "high" if any(s in line for s in ["MS17", "CVE", "RCE"]) else "medium"
                    results.append({
                        "title": line[:200],
                        "vuln_type": "other",
                        "severity": severity,
                        "detail": line,
                        "found_by": "fscan",
                        "dedup_hash": _dedup_hash("fscan", line[:100]),
                    })
    except Exception as e:
        logger.error(f"[fscan] Parse failed for {file_path}: {e}", exc_info=True)
    return results
