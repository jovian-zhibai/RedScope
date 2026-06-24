"""AI-powered report writer: generates vulnerability descriptions and fix suggestions."""

from backend.ai.llm_client import get_llm_client

VULN_DESCRIPTION_PROMPT = """你是一名资深渗透测试工程师，正在撰写渗透测试报告。
请根据以下漏洞信息，生成专业的中文漏洞描述，包括:
1. 漏洞概述（2-3句话）
2. 风险影响（攻击者能做什么）
3. 详细修复建议（具体到配置或代码层面）

要求简洁专业，不要使用模板化语言。"""

REPORT_SUMMARY_PROMPT = """你是一名资深渗透测试工程师。请根据以下漏洞统计数据，撰写一段渗透测试报告的"总结与建议"章节。
要求:
- 概述整体安全状况（好/一般/差）
- 指出最关键的风险点
- 给出3-5条优先整改建议
- 语气专业但不夸大风险"""


async def generate_vuln_description(title: str, vuln_type: str, severity: str, raw_detail: str = "") -> dict:
    client = get_llm_client()
    if not client.api_key:
        return {"description": "", "solution": "", "error": "LLM API key not configured"}

    user_msg = f"漏洞名称: {title}\n漏洞类型: {vuln_type}\n严重程度: {severity}\n原始信息: {raw_detail[:1000]}"
    try:
        result = await client.chat(VULN_DESCRIPTION_PROMPT, user_msg)
        parts = result.split("修复建议")
        description = parts[0].strip()
        solution = parts[1].strip() if len(parts) > 1 else ""
        return {"description": description, "solution": solution}
    except Exception as e:
        return {"description": "", "solution": "", "error": str(e)}


async def generate_report_summary(stats: dict) -> str:
    client = get_llm_client()
    if not client.api_key:
        return ""

    user_msg = (
        f"漏洞总数: {stats.get('total', 0)}\n"
        f"严重: {stats.get('critical', 0)}, 高危: {stats.get('high', 0)}, "
        f"中危: {stats.get('medium', 0)}, 低危: {stats.get('low', 0)}\n"
        f"资产总数: {stats.get('assets', 0)}\n"
        f"修复率: {stats.get('fix_rate', 0)}%\n"
        f"主要漏洞类型: {stats.get('top_types', '')}"
    )
    try:
        return await client.chat(REPORT_SUMMARY_PROMPT, user_msg)
    except Exception:
        return ""
