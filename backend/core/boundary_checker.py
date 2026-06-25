"""Boundary checker: validates all scan targets against project scope rules."""

import ipaddress
import re
from datetime import datetime, time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.project import Project, ScopeRule
from backend.models.scan_task import BoundaryViolation


class BoundaryCheckResult:
    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason


class BoundaryChecker:
    def __init__(self, project: Project, rules: list[ScopeRule]):
        self.project = project
        self.include_rules = [r for r in rules if r.rule_type == "include" and r.is_active]
        self.exclude_rules = [r for r in rules if r.rule_type == "exclude" and r.is_active]

    def check_target(self, target: str, port: int | None = None) -> BoundaryCheckResult:
        if self.project.mode == "research":
            if self._is_public_ip(target):
                return BoundaryCheckResult(False, f"研究模式禁止扫描公网 IP: {target}。如需测试公网目标，请切换到实战模式并配置授权。")
            return BoundaryCheckResult(True)

        if self.project.mode == "range":
            if self._is_public_ip(target):
                return BoundaryCheckResult(False, f"靶场模式检测到公网IP: {target}，请确认是否有权测试")
            return BoundaryCheckResult(True)

        # Combat mode: strict checking
        if self.project.auth_end_date and datetime.now().date() > self.project.auth_end_date:
            return BoundaryCheckResult(False, "授权已过期")

        if self.project.time_window_start and self.project.time_window_end:
            now = datetime.now().time()
            if not self._in_time_window(now, self.project.time_window_start, self.project.time_window_end):
                return BoundaryCheckResult(False, f"当前时间不在允许的测试窗口内 ({self.project.time_window_start}-{self.project.time_window_end})")

        for rule in self.exclude_rules:
            if self._match_rule(target, port, rule):
                return BoundaryCheckResult(False, f"目标命中黑名单: {rule.target_value} ({rule.description or ''})")

        if not self.include_rules:
            return BoundaryCheckResult(False, "实战模式未设置白名单")

        for rule in self.include_rules:
            if self._match_rule(target, port, rule):
                return BoundaryCheckResult(True)

        return BoundaryCheckResult(False, f"目标 {target} 不在授权范围内")

    def _match_rule(self, target: str, port: int | None, rule: ScopeRule) -> bool:
        if rule.target_type == "ip":
            return target == rule.target_value

        if rule.target_type == "cidr":
            try:
                network = ipaddress.ip_network(rule.target_value, strict=False)
                return ipaddress.ip_address(target) in network
            except ValueError:
                return False

        if rule.target_type == "ip_range":
            parts = rule.target_value.split("-")
            if len(parts) == 2:
                try:
                    start = ipaddress.ip_address(parts[0].strip())
                    end = ipaddress.ip_address(parts[1].strip())
                    addr = ipaddress.ip_address(target)
                    return start <= addr <= end
                except ValueError:
                    return False

        if rule.target_type == "domain":
            pattern = rule.target_value.replace(".", r"\.").replace("*", r"[^.]*")
            return bool(re.match(f"^{pattern}$", target, re.IGNORECASE))

        if rule.target_type == "url":
            pattern = rule.target_value.replace("*", ".*")
            return bool(re.match(f"^{pattern}$", target, re.IGNORECASE))

        if rule.target_type == "port" and port is not None:
            allowed_ports = self._parse_ports(rule.target_value)
            return port in allowed_ports

        return False

    @staticmethod
    def _is_public_ip(target: str) -> bool:
        try:
            addr = ipaddress.ip_address(target)
            return not (addr.is_private or addr.is_loopback or addr.is_link_local)
        except ValueError:
            return False

    @staticmethod
    def _in_time_window(now: time, start: time, end: time) -> bool:
        if start <= end:
            return start <= now <= end
        # Overnight window (e.g., 22:00 - 06:00)
        return now >= start or now <= end

    @staticmethod
    def _parse_ports(port_str: str) -> set[int]:
        ports = set()
        for part in port_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-")
                ports.update(range(int(start), int(end) + 1))
            else:
                ports.add(int(part))
        return ports


async def load_boundary_checker(db: AsyncSession, project_id: int) -> BoundaryChecker:
    project = await db.get(Project, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")
    result = await db.execute(
        select(ScopeRule).where(ScopeRule.project_id == project_id)
    )
    rules = list(result.scalars().all())
    return BoundaryChecker(project, rules)


async def log_violation(
    db: AsyncSession,
    project_id: int,
    target: str,
    violation_type: str,
    detail: str,
    scan_task_id: int | None = None,
):
    violation = BoundaryViolation(
        project_id=project_id,
        scan_task_id=scan_task_id,
        target=target,
        violation_type=violation_type,
        detail=detail,
    )
    db.add(violation)
    await db.flush()
