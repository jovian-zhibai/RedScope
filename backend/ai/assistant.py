"""AI Security Assistant: chat-based security analysis, smart recommendations, and attack path inference."""

from backend.ai.llm_client import get_llm_client

ASSISTANT_SYSTEM_PROMPT = """你是 RedScope 安全助手，一个专业的渗透测试 AI 顾问。你的职责：
1. 回答安全测试相关问题
2. 分析漏洞并给出修复建议
3. 根据资产信息推荐扫描策略
4. 推导攻击路径和横向移动方案
5. 帮助编写渗透测试报告
6. CTF 竞赛辅助（题目分析、解题思路、Flag获取指导）

回答要求：
- 使用中文
- 专业简洁，直接给出可操作的建议
- 涉及具体漏洞时给出 CVE 编号和 PoC 参考
- 涉及工具时给出具体命令示例
- CTF模式下，详细分析题目类型（Web/Pwn/Crypto/Misc/Reverse），给出完整解题步骤和payload"""

SCAN_RECOMMEND_PROMPT = """你是渗透测试扫描策略专家。根据以下资产指纹信息，推荐最佳扫描方案。

要求：
1. 推荐具体的扫描工具和模板
2. 给出扫描顺序（先侦察后利用）
3. 标注需要注意的风险点
4. 如果识别到已知漏洞框架，直接推荐对应 PoC

输出 JSON 格式：
{"recommendations": [{"tool": "nuclei", "templates": ["cve-2024-xxx"], "reason": "...", "priority": 1}], "warnings": ["..."], "attack_surface": "..."}"""

ATTACK_PATH_PROMPT = """你是一名高级红队专家。请根据以下已发现的漏洞和已控资产信息，推导可能的攻击路径。

要求：
1. 从初始访问点开始，逐步推导到最终目标（域控/核心数据库/管理后台）
2. 每一步标注所利用的漏洞和技术
3. 标注 ATT&CK 技术编号
4. 给出成功概率评估
5. 标注可能的防御检测点

输出结构化的攻击链，每步包含：step, action, technique(ATT&CK ID), target, prerequisite, risk_level"""

NL_QUERY_PROMPT = """你是 RedScope 数据库查询助手。用户会用自然语言描述他想查找的数据，你需要将其转换为 SQL WHERE 条件。

可用的表和字段：
- findings: id, title, vuln_type, severity(critical/high/medium/low/info), fix_status(unfixed/fixing/fixed/merged), is_verified, found_by, created_at
- assets: id, host, port, application, server, importance(critical/normal/low), is_alive, scope_status, discovered_by

只输出 JSON 格式: {"table": "findings|assets", "conditions": [{"field": "severity", "op": "=", "value": "critical"}, ...], "order_by": "created_at DESC", "description": "中文描述"}
不要输出 SQL 语句。不要加其他文字。"""


async def chat_with_assistant(message: str, context: str = "", history: list[dict] | None = None) -> str:
    client = get_llm_client()
    if not client.api_key:
        return "AI 助手未配置。请在 .env 中设置 LLM_API_KEY。"

    user_msg = message
    if context:
        user_msg = f"当前项目上下文：\n{context}\n\n用户问题：{message}"

    return await client.chat(ASSISTANT_SYSTEM_PROMPT, user_msg, history=history)


async def recommend_scan_strategy(asset_info: list[dict]) -> dict:
    client = get_llm_client()
    if not client.api_key:
        return {"error": "LLM API key not configured"}

    import json
    user_msg = f"资产指纹信息：\n{json.dumps(asset_info[:20], ensure_ascii=False, indent=2)}"
    try:
        result = await client.chat(SCAN_RECOMMEND_PROMPT, user_msg)
        return json.loads(result)
    except Exception as e:
        return {"recommendations": [], "error": str(e)}


async def infer_attack_path(findings: list[dict], compromised_hosts: list[dict], assets: list[dict]) -> str:
    client = get_llm_client()
    if not client.api_key:
        return "AI 助手未配置。"

    import json
    user_msg = (
        f"已发现漏洞 ({len(findings)} 个)：\n{json.dumps(findings[:30], ensure_ascii=False, indent=2)}\n\n"
        f"已控主机 ({len(compromised_hosts)} 台)：\n{json.dumps(compromised_hosts[:10], ensure_ascii=False, indent=2)}\n\n"
        f"资产信息 ({len(assets)} 个)：\n{json.dumps(assets[:20], ensure_ascii=False, indent=2)}"
    )
    return await client.chat(ATTACK_PATH_PROMPT, user_msg)


async def natural_language_query(question: str) -> dict:
    client = get_llm_client()
    if not client.api_key:
        return {"error": "LLM API key not configured"}

    import json
    try:
        result = await client.chat(NL_QUERY_PROMPT, question, temperature=0.1)
        return json.loads(result)
    except Exception as e:
        return {"error": str(e)}
