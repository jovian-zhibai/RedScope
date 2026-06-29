"""Scan worker: executes scan tasks asynchronously via Celery."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.tasks.celery_app import celery_app
from backend.config import get_settings
from backend.database_sync import SyncSession
from backend.core.plugin_manager import plugin_manager, PluginConfig
from backend.core.engine_orchestrator import EngineOrchestrator
from backend.core.boundary_checker import BoundaryChecker
from backend.models.project import Project, ScopeRule
from backend.models.scan_task import ScanTask, EngineRun
from backend.models.asset import Asset
from backend.models.finding import Finding

settings = get_settings()

plugin_manager.load_all()


STRATEGY_ENGINES = {
    "quick": ["nmap"],
    "standard": ["nmap", "nuclei"],
    "deep": ["nmap", "nuclei", "httpx", "dirsearch"],
    "passive": ["subfinder", "httpx"],
}


def _engines_for_strategy(strategy: str) -> list[str]:
    return STRATEGY_ENGINES.get(strategy, STRATEGY_ENGINES["standard"])


WEB_ENGINES = {"nuclei", "httpx", "dirsearch", "ffuf", "sqlmap", "whatweb", "wafw00f", "afrog"}
PORT_ENGINES = {"nmap", "fscan"}


def _build_params(target: str, engine_name: str) -> dict:
    params = {"target": target, "url": target, "domain": target}

    has_scheme = "://" in target
    host = target
    port = None

    if not has_scheme and ":" in target:
        h, _, p = target.rpartition(":")
        if p.isdigit():
            host = h
            port = p

    if engine_name in PORT_ENGINES:
        params["target"] = host
        params["domain"] = host
        if port:
            params["ports"] = port
    elif engine_name in WEB_ENGINES:
        if not has_scheme:
            url = f"http://{target}"
            params["target"] = url
            params["url"] = url
        params["domain"] = host

    return params


def _import_parser(parser_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("parser", parser_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@celery_app.task(bind=True, name="run_scan_task")
def run_scan_task(self, scan_task_id: int):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run_scan_task_async(self, scan_task_id))
    finally:
        loop.close()


async def _run_scan_task_async(task_self, scan_task_id: int):
    with SyncSession() as db:
        task = db.get(ScanTask, scan_task_id)
        if not task:
            return {"error": "Task not found"}

        task.status = "running"
        task.started_at = datetime.now()
        db.commit()

        project = db.get(Project, task.project_id)
        rules = db.execute(
            select(ScopeRule).where(ScopeRule.project_id == task.project_id)
        ).scalars().all()
        checker = BoundaryChecker(project, rules)

        engines = task.engines or _engines_for_strategy(task.scan_strategy)
        targets = task.target_assets or []
        total_vulns = 0
        skipped_targets = []
        total_steps = len(engines) * len(targets)
        completed_steps = 0

        for engine_idx, engine_name in enumerate(engines):
            plugin = plugin_manager.get_plugin(engine_name)
            if not plugin:
                engine_run = EngineRun(
                    scan_task_id=task.id, engine_name=engine_name, status="failed",
                    started_at=datetime.now(), finished_at=datetime.now(),
                    error_message=f"插件 '{engine_name}' 未找到，请检查插件是否已加载",
                )
                db.add(engine_run)
                db.commit()
                continue

            engine_run = EngineRun(
                scan_task_id=task.id,
                engine_name=engine_name,
                status="running",
                started_at=datetime.now(),
            )
            db.add(engine_run)
            db.commit()

            engine_vulns = 0
            try:
                from backend.core.engine_orchestrator import orchestrator
                from backend.core.proxy_router import ProxyRouter
                proxy_router = ProxyRouter(db, task.project_id)

                for i, target in enumerate(targets):
                    check = checker.check_target(target)
                    if not check.allowed:
                        skipped_targets.append(f"{target}: {check.reason}")
                        task.scanned_count = i + 1
                        completed_steps += 1
                        task.progress = int(completed_steps / total_steps * 100) if total_steps > 0 else 100
                        db.commit()
                        continue

                    proxy_url = None
                    route = proxy_router.get_route(target)
                    if route:
                        proxy_url = route.proxy_url

                    params = _build_params(target, engine_name)
                    result = await orchestrator.run_engine(plugin, params, proxy_url=proxy_url, task_id=f"{task.id}_{engine_name}_{i}")

                    import logging
                    logging.getLogger("scan_worker").info(f"[{engine_name}] target={target} success={result.success} output_path={result.output_path} error={result.error[:200] if result.error else ''}")

                    if result.job_id:
                        engine_run.runner_job_id = result.job_id
                        db.commit()

                    if result.success and result.output_path:
                        findings = _parse_results(db, plugin, result.output_path, task.project_id)
                        engine_vulns += len(findings)
                        total_vulns += len(findings)

                        # Instant notification for critical findings
                        critical_findings = [f for f in findings if f.severity == "critical"]
                        if critical_findings:
                            await _notify_critical_instant(critical_findings, task.task_name or f"扫描#{task.id}")

                    if not result.success:
                        engine_run.error_message = (engine_run.error_message or "") + (result.error or "")[:1000]

                    task.scanned_count = i + 1
                    completed_steps += 1
                    task.progress = int(completed_steps / total_steps * 100) if total_steps > 0 else 100
                    db.commit()
                    task_self.update_state(state="PROGRESS", meta={"progress": task.progress})

                engine_run.status = "completed"
                engine_run.vulns_found = engine_vulns
                engine_run.finished_at = datetime.now()
                # Always store stderr summary for debugging
                if result.error and not engine_run.error_message:
                    engine_run.error_message = result.error[:1000]
                if skipped_targets:
                    engine_run.error_message = (engine_run.error_message or "") + f"\n跳过 {len(skipped_targets)} 个目标: " + "; ".join(skipped_targets[:5])

            except Exception as e:
                engine_run.status = "failed"
                engine_run.error_message = str(e)[:2000]
                engine_run.finished_at = datetime.now()

            db.commit()

        failed_run = db.execute(
            select(EngineRun).where(EngineRun.scan_task_id == task.id, EngineRun.status == "failed")
        ).scalars().first()
        task.status = "failed" if failed_run and total_vulns == 0 else "completed"
        task.vulns_found = total_vulns
        task.finished_at = datetime.now()
        db.commit()

        # Post-scan: dedup + risk scoring
        try:
            from backend.core.dedup import dedup_findings
            dedup_findings(db, task.project_id)
        except Exception as e:
            import logging
            logging.getLogger("scan_worker").error(f"Dedup failed for project {task.project_id}: {e}")

        try:
            from backend.core.risk_scorer import compute_risk_score
            from backend.models.asset import Asset as AssetModel
            findings_to_score = db.execute(
                select(Finding).where(Finding.project_id == task.project_id, Finding.combined_risk_score == None, Finding.deleted_at == None)
            ).scalars().all()
            for f in findings_to_score:
                asset = db.get(AssetModel, f.asset_id) if f.asset_id else None
                f.combined_risk_score = compute_risk_score(
                    severity=f.severity or "medium",
                    asset_importance=asset.importance if asset else "normal",
                )
            db.commit()
        except Exception as e:
            import logging
            logging.getLogger("scan_worker").error(f"Risk scoring failed for project {task.project_id}: {e}")

        # Post-scan: send notification
        try:
            from backend.config import get_settings as _get_settings
            _settings = _get_settings()
            if _settings.notify_webhook_url:
                from backend.core.notify import notify_scan_complete
                await notify_scan_complete(
                    _settings.notify_webhook_url, _settings.notify_channel,
                    task.task_name or f"扫描任务#{task.id}", total_vulns,
                )
        except Exception as e:
            import logging
            logging.getLogger("scan_worker").error(f"Notification failed for task {task.id}: {e}")

    return {"task_id": scan_task_id, "vulns_found": total_vulns}


async def _notify_critical_instant(findings, task_name: str):
    try:
        _settings = get_settings()
        if not _settings.notify_webhook_url:
            return
        titles = ", ".join(f.title[:50] for f in findings[:3])
        message = f"🚨 紧急: 扫描「{task_name}」发现 {len(findings)} 个严重漏洞!\n{titles}"
        from backend.core.notify import send_webhook
        await send_webhook(_settings.notify_channel, _settings.notify_webhook_url, "RedScope 严重漏洞告警", message)
    except Exception as e:
        import logging
        logging.getLogger("scan_worker").warning(f"Failed to send critical instant notification: {e}")


def _parse_results(db: Session, plugin: PluginConfig, output_dir: str, project_id: int) -> list:
    from backend.parsers.builtin import parse_output
    parsed_data = parse_output(plugin.name, plugin.output_format, output_dir, plugin.output_path)
    created_findings = []
    for f in parsed_data:
        if f.get("type") == "asset":
            existing = db.execute(
                select(Asset).where(
                    Asset.project_id == project_id,
                    Asset.host == f.get("host", ""),
                    Asset.port == f.get("port"),
                )
            ).scalar_one_or_none()
            if existing:
                if f.get("product"):
                    existing.application = f["product"]
                if f.get("version"):
                    existing.app_version = f["version"]
                if f.get("service"):
                    existing.server = f["service"]
                if f.get("server"):
                    existing.server = f["server"]
                if f.get("url"):
                    existing.url = f["url"]
                if f.get("tech_stack"):
                    existing.fingerprint_raw = f["tech_stack"]
                existing.last_seen_at = datetime.now()
                existing.discovered_by = plugin.name
            else:
                asset = Asset(
                    project_id=project_id,
                    asset_type=f.get("asset_type", "ip"),
                    host=f.get("host", ""),
                    port=f.get("port"),
                    protocol=f.get("protocol"),
                    url=f.get("url"),
                    server=f.get("service") or f.get("server"),
                    application=f.get("product"),
                    app_version=f.get("version"),
                    fingerprint_raw=f.get("tech_stack"),
                    discovered_by=plugin.name,
                    is_alive=True,
                )
                db.add(asset)
        else:
            asset_id = None
            host = f.get("host", "")
            if host:
                from urllib.parse import urlparse
                parsed = urlparse(host) if "://" in host else urlparse(f"http://{host}")
                lookup_host = parsed.hostname or host
                lookup_port = parsed.port
                asset_query = select(Asset).where(Asset.project_id == project_id, Asset.host == lookup_host)
                if lookup_port:
                    asset_query = asset_query.where(Asset.port == lookup_port)
                matched_asset = db.execute(asset_query).scalars().first()
                if matched_asset:
                    asset_id = matched_asset.id

            finding = Finding(
                project_id=project_id,
                asset_id=asset_id,
                title=f.get("title", "Unknown"),
                vuln_type=f.get("vuln_type"),
                severity=f.get("severity", "info"),
                cvss_score=f.get("cvss_score"),
                description=f.get("description"),
                detail=f.get("detail"),
                solution=f.get("solution"),
                found_by=plugin.name,
                evidence=f.get("evidence"),
                dedup_hash=f.get("dedup_hash"),
            )
            db.add(finding)
            created_findings.append(finding)
    db.commit()
    return created_findings


@celery_app.task(name="intel_sync")
def sync_vulnerability_intel():
    from backend.intel.nvd_fetcher import fetch_latest as fetch_nvd
    from backend.intel.cnvd_fetcher import fetch_latest as fetch_cnvd
    fetch_nvd()
    fetch_cnvd()


@celery_app.task(name="asset_monitor")
def monitor_asset_changes(project_id: int):
    pass
