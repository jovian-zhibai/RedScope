"""Baseline scanning API: runs compliance checks against target hosts."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.baseline_scanner import ALL_BASELINES, evaluate_check

router = APIRouter()


class BaselineRunRequest(BaseModel):
    target: str = ""


@router.get("/baselines")
async def list_baselines(request: Request):
    return {"items": [
        {"key": k, "name": v["name"], "item_count": len(v["items"])}
        for k, v in ALL_BASELINES.items()
    ]}


@router.get("/baselines/{baseline_key}")
async def get_baseline_detail(baseline_key: str, request: Request):
    baseline = ALL_BASELINES.get(baseline_key)
    if not baseline:
        raise HTTPException(404, "基线不存在")

    return {
        "name": baseline["name"],
        "items": [
            {
                "id": item.id,
                "category": item.category,
                "title": item.title,
                "description": item.description,
                "check_command": item.check_command,
                "severity": item.severity,
                "remediation": item.remediation,
                "standard": item.standard,
            }
            for item in baseline["items"]
        ],
    }


class BaselineRunRequest(BaseModel):
    baseline_key: str
    target_host: str
    ssh_user: str = "root"
    ssh_port: int = 22
    auth_method: str = "password"  # password / key
    credential_id: int | None = None


@router.post("/baselines/{baseline_key}/run")
async def run_baseline_check(baseline_key: str, req: BaselineRunRequest = BaselineRunRequest(), request: Request = None, db: AsyncSession = Depends(get_db)):
    if request and request.state.role not in ("admin", "leader", "engineer"):
        raise HTTPException(403, "无权限执行基线扫描")
    baseline = ALL_BASELINES.get(baseline_key)
    if not baseline:
        raise HTTPException(404, "基线不存在")

    # In production: SSH to target and execute each check_command
    # For now: return the checklist with commands for manual execution
    return {
        "status": "manual_mode",
        "message": "请在目标主机上逐项执行以下检查命令，将结果填入平台",
        "baseline": baseline["name"],
        "target": req.target,
        "checks": [
            {
                "id": item.id,
                "title": item.title,
                "category": item.category,
                "severity": item.severity,
                "command": item.check_command,
                "expected": item.expected,
                "remediation": item.remediation,
            }
            for item in baseline["items"]
        ],
    }


class BaselineResultSubmit(BaseModel):
    baseline_key: str
    results: list[dict]  # [{"item_id": "L-AUTH-01", "actual_output": "8"}, ...]


@router.post("/baselines/evaluate")
async def evaluate_baseline_results(req: BaselineResultSubmit, request: Request):
    baseline = ALL_BASELINES.get(req.baseline_key)
    if not baseline:
        raise HTTPException(404, "基线不存在")

    item_map = {item.id: item for item in baseline["items"]}
    results = []
    passed_count = 0

    for r in req.results:
        item = item_map.get(r["item_id"])
        if not item:
            continue
        check_result = evaluate_check(item, r.get("actual_output", ""))
        if check_result.passed:
            passed_count += 1
        results.append({
            "item_id": item.id,
            "title": item.title,
            "category": item.category,
            "severity": item.severity,
            "passed": check_result.passed,
            "actual_value": check_result.actual_value,
            "detail": check_result.detail,
            "remediation": item.remediation if not check_result.passed else "",
        })

    total = len(results)
    return {
        "baseline": baseline["name"],
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "compliance_rate": round(passed_count / total * 100, 1) if total > 0 else 0,
        "results": results,
    }
