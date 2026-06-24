"""MITRE ATT&CK mapping: maps actions to ATT&CK techniques."""

TECHNIQUE_MAP = {
    "recon": {
        "subfinder": ("T1596.002", "搜索开放的技术数据库: DNS"),
        "nmap": ("T1046", "网络服务扫描"),
        "httpx": ("T1592", "收集受害者主机信息"),
        "dirsearch": ("T1083", "文件和目录发现"),
        "whois": ("T1596.002", "搜索WHOIS数据"),
    },
    "vuln_scan": {
        "nuclei": ("T1595.002", "漏洞扫描"),
        "sqlmap": ("T1190", "利用面向公众的应用"),
        "afrog": ("T1595.002", "漏洞扫描"),
    },
    "credential": {
        "mimikatz": ("T1003.001", "LSASS内存凭据转储"),
        "hashcat": ("T1110.002", "密码破解"),
        "kerberoast": ("T1558.003", "Kerberoasting"),
        "secretsdump": ("T1003.003", "NTDS凭据转储"),
        "browser_creds": ("T1555.003", "浏览器存储凭据"),
        "config_file": ("T1552.001", "文件中的凭据"),
    },
    "lateral": {
        "ssh": ("T1021.004", "SSH远程服务"),
        "rdp": ("T1021.001", "RDP远程桌面"),
        "psexec": ("T1569.002", "服务执行"),
        "wmiexec": ("T1047", "WMI执行"),
        "smb": ("T1021.002", "SMB共享"),
        "pass_the_hash": ("T1550.002", "哈希传递"),
    },
    "persistence": {
        "crontab": ("T1053.003", "Cron定时任务"),
        "scheduled_task": ("T1053.005", "Windows计划任务"),
        "webshell": ("T1505.003", "Web Shell"),
        "ssh_key": ("T1098.004", "SSH密钥持久化"),
        "startup": ("T1547.001", "注册表启动项"),
    },
    "privilege_escalation": {
        "suid": ("T1548.001", "SUID/SGID提权"),
        "kernel_exploit": ("T1068", "利用漏洞提权"),
        "sudo": ("T1548.003", "Sudo提权"),
        "token_impersonation": ("T1134.001", "令牌模拟"),
    },
    "tunnel": {
        "frp": ("T1572", "协议隧道"),
        "chisel": ("T1572", "协议隧道"),
        "ssh_tunnel": ("T1572", "协议隧道"),
        "socks_proxy": ("T1090.001", "内部代理"),
    },
}

PHASE_CN = {
    "recon": "信息收集",
    "initial_access": "初始访问",
    "execution": "执行",
    "persistence": "持久化",
    "privilege_escalation": "权限提升",
    "defense_evasion": "防御绕过",
    "credential_access": "凭据访问",
    "discovery": "发现",
    "lateral_movement": "横向移动",
    "collection": "收集",
    "command_and_control": "命令与控制",
    "exfiltration": "数据渗出",
}


def get_technique(category: str, tool_or_method: str) -> tuple[str, str]:
    cat_map = TECHNIQUE_MAP.get(category, {})
    return cat_map.get(tool_or_method.lower(), ("", ""))


def auto_detect_technique(action: str) -> tuple[str, str]:
    action_lower = action.lower()
    for category, techniques in TECHNIQUE_MAP.items():
        for key, (tid, desc) in techniques.items():
            if key in action_lower:
                return tid, desc
    return "", ""


def generate_heatmap_data(techniques: list[str]) -> dict:
    tactics = {
        "Reconnaissance": [], "Initial Access": [], "Execution": [],
        "Persistence": [], "Privilege Escalation": [], "Defense Evasion": [],
        "Credential Access": [], "Discovery": [], "Lateral Movement": [],
        "Collection": [], "Command and Control": [], "Exfiltration": [],
    }

    tactic_prefix_map = {
        "T1595": "Reconnaissance", "T1596": "Reconnaissance", "T1592": "Reconnaissance",
        "T1190": "Initial Access", "T1566": "Initial Access",
        "T1046": "Discovery", "T1083": "Discovery",
        "T1047": "Execution", "T1569": "Execution",
        "T1505": "Persistence", "T1053": "Persistence", "T1547": "Persistence", "T1098": "Persistence",
        "T1068": "Privilege Escalation", "T1548": "Privilege Escalation", "T1134": "Privilege Escalation",
        "T1003": "Credential Access", "T1110": "Credential Access", "T1558": "Credential Access",
        "T1552": "Credential Access", "T1555": "Credential Access",
        "T1021": "Lateral Movement", "T1550": "Lateral Movement",
        "T1572": "Command and Control", "T1090": "Command and Control",
    }

    for tech_id in techniques:
        base_id = tech_id.split(".")[0] if "." in tech_id else tech_id
        tactic = tactic_prefix_map.get(base_id, "")
        if tactic and tech_id not in tactics[tactic]:
            tactics[tactic].append(tech_id)

    return {tactic: {"count": len(techs), "techniques": techs} for tactic, techs in tactics.items()}
