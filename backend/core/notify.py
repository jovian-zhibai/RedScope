"""Notification system: sends alerts via webhook (WeCom, DingTalk, Feishu, Email)."""

import httpx
from enum import Enum


class NotifyChannel(str, Enum):
    WECOM = "wecom"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"


async def send_webhook(channel: str, webhook_url: str, title: str, content: str):
    if channel == NotifyChannel.WECOM:
        await _send_wecom(webhook_url, title, content)
    elif channel == NotifyChannel.DINGTALK:
        await _send_dingtalk(webhook_url, title, content)
    elif channel == NotifyChannel.FEISHU:
        await _send_feishu(webhook_url, title, content)


async def _send_wecom(url: str, title: str, content: str):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={
            "msgtype": "markdown",
            "markdown": {"content": f"### {title}\n{content}"},
        })


async def _send_dingtalk(url: str, title: str, content: str):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={
            "msgtype": "markdown",
            "markdown": {"title": title, "text": f"### {title}\n{content}"},
        })


async def _send_feishu(url: str, title: str, content: str):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": title}},
                "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content}}],
            },
        })


async def notify_critical_finding(webhook_url: str, channel: str, finding_title: str, severity: str, project_name: str):
    title = f"🚨 发现{severity}漏洞"
    content = (
        f"**项目**: {project_name}\n"
        f"**漏洞**: {finding_title}\n"
        f"**等级**: {severity}\n"
        f"**时间**: {{now}}"
    )
    from datetime import datetime
    content = content.replace("{now}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    await send_webhook(channel, webhook_url, title, content)


async def notify_scan_complete(webhook_url: str, channel: str, task_name: str, vulns_found: int):
    title = "✅ 扫描任务完成"
    content = f"**任务**: {task_name}\n**发现漏洞**: {vulns_found} 个"
    await send_webhook(channel, webhook_url, title, content)


async def notify_auth_expiring(webhook_url: str, channel: str, project_name: str, days_left: int):
    title = "⚠️ 授权即将到期"
    content = f"**项目**: {project_name}\n**剩余天数**: {days_left} 天"
    await send_webhook(channel, webhook_url, title, content)
