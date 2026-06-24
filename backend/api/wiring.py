"""Wiring API: connects all core modules (vuln matching, dedup, risk scoring,
ATT&CK mapping, OPSEC monitor, import/export, pipeline execution) to endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.database_sync import SyncSession

router = APIRouter()


# ─── Vulnerability Matching ──────────────────────────────

@router.post("/projects/{project_id}/match-vulns")
async def match_project_vulns(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.core.vuln_matcher import match_asset_vulns
    from backend.models.asset import Asset
    from backend.models.finding import Finding

    result = await db.execute(
        select(Asset).where(Asset.project_id == project_id, Asset.is_alive == True)
    )
    assets = result.scalars().all()

    # vuln_matcher uses sync session, run in executor

    matches = []
    with SyncSession() as sync_db:
        for asset in assets:
            from backend.core.vuln_matcher import match_asset_vulns as sync_match
            asset_matches = sync_match(sync_db, asset)
            for m in asset_matches:
                existing = await db.execute(
                    select(Finding).where(
                        Finding.project_id == project_id,
                        Finding.asset_id == asset.id,
                        Finding.vuln_knowledge_id == m.vuln.id,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                finding = Finding(
                    project_id=project_id,
                    asset_id=asset.id,
                    vuln_knowledge_id=m.vuln.id,
                    title=f"[被动匹配] {m.vuln.title}",
                    vuln_type=m.vuln.vuln_type,
                    severity=m.vuln.severity,
                    cvss_score=m.vuln.cvss_score,
                    description=f"{m.vuln.description}\n\n匹配依据: {m.reason}",
                    solution=m.vuln.solution,
                    found_by="vuln_matcher",
                    is_verified=False,
                    combined_risk_score=m.confidence * 10,
                )
                db.add(finding)
                matches.append({
                    "asset": f"{asset.host}:{asset.port or ''}",
                    "vuln": m.vuln.title,
                    "confidence": round(m.confidence, 2),
                    "reason": m.reason,
                })

    await db.flush()
    return {"matched": len(matches), "results": matches}


# ─── Dedup ────────────────────────────────────────────────

@router.post("/projects/{project_id}/dedup")
async def dedup_project_findings(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.config import get_settings
    from backend.core.dedup import dedup_findings

    settings = get_settings()
    sync_engine = create_engine(settings.database_url.replace("+asyncpg", ""))
    SyncSession = sessionmaker(sync_engine)

    with SyncSession() as sync_db:
        result = dedup_findings(sync_db, project_id)

    return result


# ─── Risk Scoring ─────────────────────────────────────────

@router.post("/projects/{project_id}/score-risks")
async def score_project_risks(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.models.finding import Finding
    from backend.models.asset import Asset
    from backend.core.risk_scorer import compute_risk_score, risk_label
    import ipaddress

    result = await db.execute(
        select(Finding).where(Finding.project_id == project_id, Finding.is_false_positive == False)
    )
    findings = result.scalars().all()
    updated = 0

    for f in findings:
        asset = await db.get(Asset, f.asset_id) if f.asset_id else None
        importance = asset.importance if asset else "normal"

        is_public = False
        if asset and asset.host:
            try:
                addr = ipaddress.ip_address(asset.host)
                is_public = not (addr.is_private or addr.is_loopback)
            except ValueError:
                is_public = False

        score = compute_risk_score(
            severity=f.severity or "medium",
            asset_importance=importance,
            is_public=is_public,
        )
        f.combined_risk_score = score
        updated += 1

    await db.flush()
    return {"updated": updated, "message": f"已为 {updated} 个漏洞计算综合风险评分"}


# ─── ATT&CK Mapping ──────────────────────────────────────

@router.get("/projects/{project_id}/attck-heatmap")
async def get_attck_heatmap(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.models.operational import AttackTimeline
    from backend.core.attck_mapping import generate_heatmap_data

    result = await db.execute(
        select(AttackTimeline).where(AttackTimeline.project_id == project_id)
    )
    entries = result.scalars().all()
    techniques = [e.attck_id for e in entries if e.attck_id]
    heatmap = generate_heatmap_data(techniques)
    return {"heatmap": heatmap, "total_techniques": len(set(techniques))}


@router.post("/projects/{project_id}/auto-attck")
async def auto_map_attck(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.models.operational import AttackTimeline
    from backend.core.attck_mapping import auto_detect_technique

    result = await db.execute(
        select(AttackTimeline).where(
            AttackTimeline.project_id == project_id,
            AttackTimeline.attck_id == None,
        )
    )
    entries = result.scalars().all()
    mapped = 0

    for entry in entries:
        tid, desc = auto_detect_technique(entry.action)
        if tid:
            entry.attck_id = tid
            mapped += 1

    await db.flush()
    return {"total_unmapped": len(entries), "auto_mapped": mapped}


# ─── OPSEC Monitor ────────────────────────────────────────

class OpsecCheckRequest(BaseModel):
    engine_name: str = "nuclei"
    concurrency: int = 50
    target_count: int = 1


@router.post("/projects/{project_id}/opsec-check")
async def check_opsec(project_id: int, req: OpsecCheckRequest, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.models.project import Project
    from backend.core.opsec_monitor import check_scan_opsec

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    now = datetime.now()
    is_work_hours = 9 <= now.hour <= 18 and now.weekday() < 5

    warnings = check_scan_opsec(
        engine_name=req.engine_name,
        concurrency=req.concurrency,
        target_count=req.target_count,
        is_work_hours=is_work_hours,
        project_mode=project.mode,
    )

    return {"warnings": [
        {"level": w.level, "category": w.category, "message": w.message, "suggestion": w.suggestion}
        for w in warnings
    ]}


# ─── Import / Export ──────────────────────────────────────

@router.post("/projects/{project_id}/import/csv-assets")
async def import_csv_assets(project_id: int, _=Depends(require_project), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    from backend.core.import_export import import_assets_from_csv
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.config import get_settings

    content = await file.read()
    csv_text = content.decode("utf-8-sig")

    settings = get_settings()
    sync_engine = create_engine(settings.database_url.replace("+asyncpg", ""))
    SyncSession = sessionmaker(sync_engine)

    with SyncSession() as sync_db:
        count = import_assets_from_csv(sync_db, project_id, csv_text)

    return {"imported": count, "message": f"成功导入 {count} 个资产"}


@router.post("/projects/{project_id}/import/nessus")
async def import_nessus_report(project_id: int, _=Depends(require_project), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    from backend.core.import_export import import_nessus_xml
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.config import get_settings

    content = await file.read()
    xml_text = content.decode("utf-8")

    settings = get_settings()
    sync_engine = create_engine(settings.database_url.replace("+asyncpg", ""))
    SyncSession = sessionmaker(sync_engine)

    with SyncSession() as sync_db:
        count = import_nessus_xml(sync_db, project_id, xml_text)

    return {"imported": count, "message": f"成功导入 {count} 个漏洞"}


@router.get("/projects/{project_id}/export/findings-csv")
async def export_findings_csv(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.core.import_export import export_findings_csv
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.config import get_settings
    import io

    settings = get_settings()
    sync_engine = create_engine(settings.database_url.replace("+asyncpg", ""))
    SyncSession = sessionmaker(sync_engine)

    with SyncSession() as sync_db:
        csv_content = export_findings_csv(sync_db, project_id)

    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=findings_{project_id}.csv"},
    )


@router.get("/projects/{project_id}/export/archive")
async def export_project_archive(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.core.import_export import export_project_archive
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.config import get_settings

    settings = get_settings()
    sync_engine = create_engine(settings.database_url.replace("+asyncpg", ""))
    SyncSession = sessionmaker(sync_engine)

    with SyncSession() as sync_db:
        archive = export_project_archive(sync_db, project_id)

    return archive


# ─── Pipeline Execution ──────────────────────────────────

class PipelineRunRequest(BaseModel):
    pipeline_name: str = ""
    pipeline_dag: dict | None = None
    targets: list[str] = []


@router.get("/pipelines")
async def list_pipelines():
    import yaml
    from pathlib import Path
    from backend.config import get_settings

    settings = get_settings()
    pipeline_dir = Path("/app/pipelines")
    pipelines = []

    if pipeline_dir.exists():
        for f in pipeline_dir.glob("*.yaml"):
            try:
                with open(f) as fh:
                    data = yaml.safe_load(fh)
                pipelines.append({
                    "file": f.stem,
                    "name": data.get("name", f.stem),
                    "description": data.get("description", ""),
                    "node_count": len(data.get("nodes", [])),
                })
            except Exception:
                pass

    return {"items": pipelines}


@router.post("/projects/{project_id}/run-pipeline")
async def run_pipeline(project_id: int, req: PipelineRunRequest, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    import yaml
    from pathlib import Path
    from backend.core.boundary_checker import load_boundary_checker

    checker = await load_boundary_checker(db, project_id)
    violations = []
    for target in req.targets:
        check = checker.check_target(target)
        if not check.allowed:
            violations.append({"target": target, "reason": check.reason})
    if violations:
        raise HTTPException(400, detail={"message": "目标越界", "violations": violations})

    dag = req.pipeline_dag
    if not dag and req.pipeline_name:
        pipeline_file = Path(f"/app/pipelines/{req.pipeline_name}.yaml")
        if not pipeline_file.exists():
            raise HTTPException(404, f"流水线 {req.pipeline_name} 不存在")
        with open(pipeline_file) as f:
            data = yaml.safe_load(f)
        dag = {"nodes": data.get("nodes", []), "edges": data.get("edges", [])}

    if not dag:
        raise HTTPException(400, "未指定流水线配置")

    from backend.core.pipeline_executor import PipelineExecutor
    executor = PipelineExecutor()
    results = await executor.execute(dag, req.targets)
    return {"status": "completed", "results": results}


# ─── LLM Security Testing ────────────────────────────────

class LLMTestRequest(BaseModel):
    target_url: str
    api_key: str = ""
    headers: dict | None = None


@router.post("/projects/{project_id}/llm-security-test")
async def run_llm_security_test(project_id: int, req: LLMTestRequest, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.ai.llm_security_test import LLMSecurityTester

    tester = LLMSecurityTester(
        target_url=req.target_url,
        api_key=req.api_key,
        headers=req.headers,
    )
    results = await tester.run_all_tests()

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    from backend.models.finding import Finding
    for r in results:
        if not r.passed:
            finding = Finding(
                project_id=project_id,
                title=f"[LLM安全] {r.test_name}",
                vuln_type="llm_security",
                severity=r.risk_level,
                description=f"分类: {r.category}\n{r.detail}",
                detail=f"攻击Prompt:\n{r.prompt}\n\nAI响应:\n{r.response}",
                solution="检查系统提示词防护,加强输入过滤和输出审核",
                found_by="llm_security_test",
            )
            db.add(finding)

    await db.flush()

    return {
        "total": len(results), "passed": passed, "failed": failed,
        "results": [
            {"test_name": r.test_name, "category": r.category, "passed": r.passed,
             "risk_level": r.risk_level, "detail": r.detail,
             "prompt": r.prompt[:200], "response": r.response[:200]}
            for r in results
        ],
    }


# ─── AI Report Writing ───────────────────────────────────

@router.post("/projects/{project_id}/ai-vuln-description")
async def ai_generate_vuln_description(project_id: int, req: dict, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.ai.report_writer import generate_vuln_description
    result = await generate_vuln_description(
        title=req.get("title", ""),
        vuln_type=req.get("vuln_type", ""),
        severity=req.get("severity", ""),
        raw_detail=req.get("raw_detail", ""),
    )
    return result


@router.post("/projects/{project_id}/ai-report-summary")
async def ai_generate_report_summary(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.ai.report_writer import generate_report_summary
    from backend.models.finding import Finding
    from sqlalchemy import func

    total = await db.scalar(select(func.count()).where(Finding.project_id == project_id))
    severities = {}
    for sev in ["critical", "high", "medium", "low"]:
        severities[sev] = await db.scalar(
            select(func.count()).where(Finding.project_id == project_id, Finding.severity == sev)
        )
    fixed = await db.scalar(
        select(func.count()).where(Finding.project_id == project_id, Finding.fix_status == "fixed")
    )

    summary = await generate_report_summary({
        "total": total, **severities,
        "fix_rate": round(fixed / total * 100, 1) if total > 0 else 0,
    })
    return {"summary": summary}


# ─── Notification Test ────────────────────────────────────

class NotifyTestRequest(BaseModel):
    webhook_url: str
    channel: str = "wecom"
    message: str = "RedScope 通知测试"


@router.post("/notify/test")
async def test_notification(req: NotifyTestRequest):
    from backend.core.notify import send_webhook
    try:
        await send_webhook(req.channel, req.webhook_url, "RedScope 测试通知", req.message)
        return {"status": "sent"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ─── Proxy Routing ────────────────────────────────────────

@router.get("/projects/{project_id}/proxy-route")
async def get_proxy_route(project_id: int, target: str, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.core.proxy_router import ProxyRouter
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.config import get_settings

    settings = get_settings()
    sync_engine = create_engine(settings.database_url.replace("+asyncpg", ""))
    SyncSession = sessionmaker(sync_engine)

    with SyncSession() as sync_db:
        router_inst = ProxyRouter(sync_db, project_id)
        route = router_inst.get_route(target)
        proxychains_conf = router_inst.generate_proxychains_config(target)


    if route:
        return {"proxy_url": route.proxy_url, "chain": route.chain, "proxychains_config": proxychains_conf}
    return {"proxy_url": None, "chain": [], "message": "该目标可直连,无需代理"}
