"""OPSEC monitor: warns about behaviors that may trigger detection."""

from dataclasses import dataclass


@dataclass
class OpsecWarning:
    level: str  # warning / danger
    category: str
    message: str
    suggestion: str


def check_scan_opsec(
    engine_name: str,
    concurrency: int,
    target_count: int,
    is_work_hours: bool = False,
    project_mode: str = "combat",
) -> list[OpsecWarning]:
    if project_mode != "combat":
        return []

    warnings = []

    if concurrency > 100:
        warnings.append(OpsecWarning(
            level="danger", category="扫描速率",
            message=f"并发数 {concurrency} 过高，可能触发IDS/WAF告警",
            suggestion="建议将并发降至50以下，或使用慢速扫描模式",
        ))
    elif concurrency > 50:
        warnings.append(OpsecWarning(
            level="warning", category="扫描速率",
            message=f"并发数 {concurrency} 较高，存在触发告警风险",
            suggestion="建议在非业务高峰期进行扫描",
        ))

    if is_work_hours:
        warnings.append(OpsecWarning(
            level="warning", category="时间窗口",
            message="当前处于工作时间，大量扫描流量容易被安全运维人员注意",
            suggestion="建议在非工作时间(22:00-06:00)进行高强度扫描",
        ))

    ua_exposed_tools = ["nuclei", "sqlmap", "dirsearch", "nikto"]
    if engine_name in ua_exposed_tools:
        warnings.append(OpsecWarning(
            level="warning", category="工具指纹",
            message=f"{engine_name} 默认User-Agent包含工具特征，容易被WAF识别",
            suggestion=f"建议自定义User-Agent，如添加 -H 'User-Agent: Mozilla/5.0 ...'",
        ))

    if engine_name == "nmap" and target_count > 100:
        warnings.append(OpsecWarning(
            level="warning", category="扫描范围",
            message=f"Nmap扫描 {target_count} 个目标，SYN扫描会产生大量半连接",
            suggestion="建议分批扫描，每批不超过50个目标，间隔5-10分钟",
        ))

    return warnings


def check_brute_opsec(target: str, attempt_count: int) -> list[OpsecWarning]:
    warnings = []
    if attempt_count > 50:
        warnings.append(OpsecWarning(
            level="danger", category="暴力破解",
            message=f"对 {target} 已产生 {attempt_count} 次失败认证，可能触发账户锁定",
            suggestion="建议暂停爆破，改用密码喷洒(每个账户只试2-3个密码)",
        ))
    elif attempt_count > 20:
        warnings.append(OpsecWarning(
            level="warning", category="暴力破解",
            message=f"对 {target} 已产生 {attempt_count} 次失败认证",
            suggestion="注意观察账户是否被锁定，考虑增加请求间隔",
        ))
    return warnings
