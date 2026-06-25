"""Wiring API: connects all core modules (vuln matching, dedup, risk scoring,
ATT&CK mapping, OPSEC monitor, import/export, pipeline execution) to endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
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
    from backend.core.dedup import dedup_findings
    from backend.database_sync import SyncSession as SS

    with SS() as sync_db:
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

    now = datetime.now(tz=None)  # Server local time for OPSEC window check
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
    from backend.database_sync import SyncSession as SS

    content = await file.read()
    csv_text = content.decode("utf-8-sig")

    with SS() as sync_db:
        count = import_assets_from_csv(sync_db, project_id, csv_text)

    return {"imported": count, "message": f"成功导入 {count} 个资产"}


@router.post("/projects/{project_id}/import/nessus")
async def import_nessus_report(project_id: int, _=Depends(require_project), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    from backend.core.import_export import import_nessus_xml
    from backend.database_sync import SyncSession as SS

    content = await file.read()
    xml_text = content.decode("utf-8")

    with SS() as sync_db:
        count = import_nessus_xml(sync_db, project_id, xml_text)

    return {"imported": count, "message": f"成功导入 {count} 个漏洞"}


@router.get("/projects/{project_id}/export/findings-csv")
async def export_findings_csv(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.core.import_export import export_findings_csv
    from backend.database_sync import SyncSession as SS
    import io

    with SS() as sync_db:
        csv_content = export_findings_csv(sync_db, project_id)

    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=findings_{project_id}.csv"},
    )


@router.get("/projects/{project_id}/export/archive")
async def export_project_archive(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.core.import_export import export_project_archive
    from backend.database_sync import SyncSession as SS

    with SS() as sync_db:
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
    from backend.core.ssrf_filter import validate_url_not_internal
    validate_url_not_internal(req.target_url)

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
async def test_notification(req: NotifyTestRequest, request: Request):
    if not hasattr(request.state, 'role') or request.state.role != 'admin':
        raise HTTPException(403, "仅管理员可测试通知")
    from backend.core.notify import send_webhook
    from backend.core.ssrf_filter import validate_url_not_internal
    validate_url_not_internal(req.webhook_url)
    try:
        await send_webhook(req.channel, req.webhook_url, "RedScope 测试通知", req.message)
        return {"status": "sent"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ─── Proxy Routing ────────────────────────────────────────

@router.get("/projects/{project_id}/proxy-route")
async def get_proxy_route(project_id: int, target: str, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.core.proxy_router import ProxyRouter
    from backend.database_sync import SyncSession as SS

    with SS() as sync_db:
        router_inst = ProxyRouter(sync_db, project_id)
        route = router_inst.get_route(target)
        proxychains_conf = router_inst.generate_proxychains_config(target)

    if route:
        return {"proxy_url": route.proxy_url, "chain": route.chain, "proxychains_config": proxychains_conf}
    return {"proxy_url": None, "chain": [], "message": "该目标可直连,无需代理"}


# ─── AI Security Assistant ──────────────────────────────


class AIChatRequest(BaseModel):
    message: str
    project_id: int | None = None


class AIScanRecommendRequest(BaseModel):
    asset_ids: list[int] = []


@router.post("/ai/chat")
async def ai_chat(req: AIChatRequest, request: Request, db: AsyncSession = Depends(get_db)):
    from backend.ai.assistant import chat_with_assistant

    context = ""
    if req.project_id:
        from backend.models.project import Project
        project = await db.get(Project, req.project_id)
        if project:
            from backend.models.finding import Finding
            from backend.models.asset import Asset
            finding_count = await db.scalar(select(func.count()).where(Finding.project_id == req.project_id))
            asset_count = await db.scalar(select(func.count()).where(Asset.project_id == req.project_id))
            context = f"项目: {project.name}, 模式: {project.mode}, 资产: {asset_count}, 漏洞: {finding_count}"

    reply = await chat_with_assistant(req.message, context)
    return {"reply": reply}


@router.post("/projects/{project_id}/ai/recommend-scan")
async def ai_recommend_scan(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.ai.assistant import recommend_scan_strategy
    from backend.models.asset import Asset

    result = await db.execute(
        select(Asset).where(Asset.project_id == project_id, Asset.deleted_at == None).limit(50)
    )
    assets = result.scalars().all()
    asset_info = [
        {"host": a.host, "port": a.port, "server": a.server, "application": a.application,
         "app_version": a.app_version, "os": a.os, "framework": a.framework}
        for a in assets
    ]
    recommendations = await recommend_scan_strategy(asset_info)
    return recommendations


@router.post("/projects/{project_id}/ai/attack-path")
async def ai_attack_path(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.ai.assistant import infer_attack_path
    from backend.models.finding import Finding
    from backend.models.asset import Asset
    from backend.models.operational import CompromisedHost

    findings_result = await db.execute(
        select(Finding).where(Finding.project_id == project_id, Finding.deleted_at == None)
        .order_by(Finding.severity).limit(30)
    )
    findings = [{"title": f.title, "severity": f.severity, "vuln_type": f.vuln_type,
                 "asset_id": f.asset_id, "fix_status": f.fix_status}
                for f in findings_result.scalars().all()]

    hosts_result = await db.execute(
        select(CompromisedHost).where(CompromisedHost.project_id == project_id)
    )
    hosts = [{"ip": h.ip, "hostname": h.hostname, "access_level": h.access_level,
              "shell_type": h.shell_type, "status": h.status}
             for h in hosts_result.scalars().all()]

    assets_result = await db.execute(
        select(Asset).where(Asset.project_id == project_id, Asset.deleted_at == None).limit(20)
    )
    assets = [{"host": a.host, "port": a.port, "server": a.server, "application": a.application}
              for a in assets_result.scalars().all()]

    path = await infer_attack_path(findings, hosts, assets)
    return {"attack_path": path}


@router.post("/ai/query")
async def ai_natural_language_query(req: AIChatRequest, request: Request, db: AsyncSession = Depends(get_db)):
    from backend.ai.assistant import natural_language_query
    from backend.models.finding import Finding
    from backend.models.asset import Asset

    parsed = await natural_language_query(req.message)
    if "error" in parsed:
        return {"error": parsed["error"], "results": []}

    table = parsed.get("table", "findings")
    conditions = parsed.get("conditions", [])
    description = parsed.get("description", "")

    ALLOWED_FINDING_FIELDS = {"severity", "vuln_type", "fix_status", "is_verified", "found_by", "title"}
    ALLOWED_ASSET_FIELDS = {"host", "port", "application", "server", "importance", "is_alive", "scope_status"}
    ALLOWED_OPS = {"=", "!=", "like"}

    if table == "findings":
        query = select(Finding)
        if req.project_id:
            query = query.where(Finding.project_id == req.project_id)
        query = query.where(Finding.deleted_at == None)
        for cond in conditions:
            field = cond.get("field")
            op = cond.get("op", "=")
            value = cond.get("value")
            if field not in ALLOWED_FINDING_FIELDS or op not in ALLOWED_OPS:
                continue
            col = getattr(Finding, field)
            if op == "=":
                query = query.where(col == value)
            elif op == "!=":
                query = query.where(col != value)
            elif op == "like":
                query = query.where(col.ilike(f"%{str(value)[:100]}%"))
        query = query.limit(50)
        result = await db.execute(query)
        items = [{"id": f.id, "title": f.title, "severity": f.severity,
                  "vuln_type": f.vuln_type, "fix_status": f.fix_status}
                 for f in result.scalars().all()]
    else:
        query = select(Asset)
        if req.project_id:
            query = query.where(Asset.project_id == req.project_id)
        query = query.where(Asset.deleted_at == None)
        for cond in conditions:
            field = cond.get("field")
            op = cond.get("op", "=")
            value = cond.get("value")
            if field not in ALLOWED_ASSET_FIELDS or op not in ALLOWED_OPS:
                continue
            col = getattr(Asset, field)
            if op == "=":
                query = query.where(col == value)
            elif op == "like":
                query = query.where(col.ilike(f"%{str(value)[:100]}%"))
        query = query.limit(50)
        result = await db.execute(query)
        items = [{"id": a.id, "host": a.host, "port": a.port,
                  "application": a.application, "importance": a.importance}
                 for a in result.scalars().all()]

    return {"description": description, "table": table, "count": len(items), "results": items}


# ─── Auto Attack Chain Builder ───────────────────────────

@router.post("/projects/{project_id}/ai/build-attack-chain")
async def ai_build_attack_chain(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.ai.assistant import infer_attack_path
    from backend.models.finding import Finding, AttackChain, AttackChainStep
    from backend.models.asset import Asset
    from backend.models.operational import CompromisedHost

    findings_result = await db.execute(
        select(Finding).where(Finding.project_id == project_id, Finding.deleted_at == None)
        .order_by(Finding.severity).limit(30)
    )
    findings = [{"id": f.id, "title": f.title, "severity": f.severity, "vuln_type": f.vuln_type, "asset_id": f.asset_id}
                for f in findings_result.scalars().all()]

    hosts_result = await db.execute(select(CompromisedHost).where(CompromisedHost.project_id == project_id))
    hosts = [{"ip": h.ip, "hostname": h.hostname, "access_level": h.access_level} for h in hosts_result.scalars().all()]

    assets_result = await db.execute(select(Asset).where(Asset.project_id == project_id, Asset.deleted_at == None).limit(20))
    assets = [{"host": a.host, "port": a.port, "server": a.server, "application": a.application} for a in assets_result.scalars().all()]

    path_text = await infer_attack_path(findings, hosts, assets)

    chain = AttackChain(
        project_id=project_id,
        chain_name=f"AI 推导攻击链 - {datetime.now().strftime('%m/%d %H:%M')}",
        description=path_text,
        combined_severity="critical" if any(f["severity"] == "critical" for f in findings) else "high",
    )
    db.add(chain)
    await db.flush()

    return {"chain_id": chain.id, "attack_path": path_text}


# ─── AI Repair Roadmap ──────────────────────────────────

@router.post("/projects/{project_id}/ai/repair-roadmap")
async def ai_repair_roadmap(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from backend.ai.llm_client import get_llm_client
    from backend.models.finding import Finding
    from backend.models.asset import Asset

    findings_result = await db.execute(
        select(Finding).where(
            Finding.project_id == project_id,
            Finding.deleted_at == None,
            Finding.fix_status.in_(["unfixed", "fixing"]),
        ).order_by(Finding.severity)
    )
    findings = findings_result.scalars().all()

    import json
    findings_data = [
        {"title": f.title, "severity": f.severity, "vuln_type": f.vuln_type,
         "cvss": float(f.cvss_score) if f.cvss_score else None,
         "risk_score": float(f.combined_risk_score) if f.combined_risk_score else None,
         "fix_status": f.fix_status}
        for f in findings
    ]

    client = get_llm_client()
    if not client.api_key:
        return {"roadmap": "AI 未配置，请设置 LLM_API_KEY", "findings_count": len(findings)}

    prompt = """你是安全顾问。根据以下未修复漏洞列表，生成一份「优先修复路线图」。

要求：
1. 按紧急程度分为：本周必修、本月重点、下季度规划
2. 每个分组说明理由（CVSS、武器化程度、资产重要性）
3. 给出具体修复建议和预估工时
4. 最后给一段给客户 CTO 看的总结（3句话）

漏洞数据："""

    roadmap = await client.chat(prompt, json.dumps(findings_data[:30], ensure_ascii=False))
    return {"roadmap": roadmap, "findings_count": len(findings)}
