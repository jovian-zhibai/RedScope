"""Baseline compliance scanner: checks host configurations against security baselines."""

from dataclasses import dataclass, field


@dataclass
class BaselineCheckItem:
    id: str
    category: str
    title: str
    description: str
    check_command: str  # 在目标主机上执行的命令
    expected: str  # 期望结果的判断条件
    severity: str  # high / medium / low
    remediation: str  # 修复建议
    standard: str  # 对应标准 (等保2.0 / CIS)


@dataclass
class BaselineCheckResult:
    item: BaselineCheckItem
    passed: bool
    actual_value: str
    detail: str


# ─── 等保2.0 三级 Linux 基线 ────────────────────────────

LINUX_BASELINE_DENGBAO3 = [
    BaselineCheckItem(
        id="L-AUTH-01", category="身份鉴别", title="密码最小长度",
        description="检查系统密码策略是否要求最小长度>=8",
        check_command="grep '^PASS_MIN_LEN' /etc/login.defs | awk '{print $2}'",
        expected=">=8", severity="high",
        remediation="编辑 /etc/login.defs, 设置 PASS_MIN_LEN 8",
        standard="等保2.0-三级-身份鉴别",
    ),
    BaselineCheckItem(
        id="L-AUTH-02", category="身份鉴别", title="密码复杂度",
        description="检查是否启用密码复杂度要求(大小写+数字+特殊字符)",
        check_command="grep 'pam_pwquality' /etc/pam.d/system-auth | grep -v '^#' | head -1",
        expected="contains:minlen", severity="high",
        remediation="在 /etc/pam.d/system-auth 中配置 pam_pwquality.so minlen=8 dcredit=-1 ucredit=-1 lcredit=-1 ocredit=-1",
        standard="等保2.0-三级-身份鉴别",
    ),
    BaselineCheckItem(
        id="L-AUTH-03", category="身份鉴别", title="密码过期时间",
        description="检查密码最长使用期限是否<=90天",
        check_command="grep '^PASS_MAX_DAYS' /etc/login.defs | awk '{print $2}'",
        expected="<=90", severity="medium",
        remediation="编辑 /etc/login.defs, 设置 PASS_MAX_DAYS 90",
        standard="等保2.0-三级-身份鉴别",
    ),
    BaselineCheckItem(
        id="L-AUTH-04", category="身份鉴别", title="登录失败锁定",
        description="检查是否配置登录失败锁定策略",
        check_command="grep 'pam_faillock\\|pam_tally2' /etc/pam.d/system-auth | grep -v '^#' | head -1",
        expected="not_empty", severity="high",
        remediation="在 /etc/pam.d/system-auth 中配置 pam_faillock.so deny=5 unlock_time=600",
        standard="等保2.0-三级-身份鉴别",
    ),
    BaselineCheckItem(
        id="L-AUTH-05", category="身份鉴别", title="SSH禁止root远程登录",
        description="检查SSH是否禁止root直接登录",
        check_command="grep '^PermitRootLogin' /etc/ssh/sshd_config | awk '{print $2}'",
        expected="equals:no", severity="high",
        remediation="编辑 /etc/ssh/sshd_config, 设置 PermitRootLogin no",
        standard="等保2.0-三级-身份鉴别",
    ),
    BaselineCheckItem(
        id="L-AUTH-06", category="身份鉴别", title="SSH协议版本",
        description="检查SSH是否使用安全的协议版本",
        check_command="ssh -V 2>&1 | head -1",
        expected="contains:OpenSSH", severity="medium",
        remediation="确保SSH版本为OpenSSH 7.0以上",
        standard="等保2.0-三级-身份鉴别",
    ),
    BaselineCheckItem(
        id="L-ACCESS-01", category="访问控制", title="空密码账户检查",
        description="检查系统中是否存在空密码账户",
        check_command="awk -F: '($2 == \"\" || $2 == \"!\") {print $1}' /etc/shadow 2>/dev/null | wc -l",
        expected="equals:0", severity="critical",
        remediation="为所有空密码账户设置密码或禁用账户",
        standard="等保2.0-三级-访问控制",
    ),
    BaselineCheckItem(
        id="L-ACCESS-02", category="访问控制", title="UID为0的非root账户",
        description="检查是否存在UID为0的非root账户",
        check_command="awk -F: '($3 == 0 && $1 != \"root\") {print $1}' /etc/passwd | wc -l",
        expected="equals:0", severity="critical",
        remediation="删除或修改多余的UID=0账户",
        standard="等保2.0-三级-访问控制",
    ),
    BaselineCheckItem(
        id="L-ACCESS-03", category="访问控制", title="重要文件权限",
        description="检查/etc/passwd和/etc/shadow文件权限",
        check_command="stat -c '%a' /etc/shadow",
        expected="equals:600", severity="high",
        remediation="执行 chmod 600 /etc/shadow",
        standard="等保2.0-三级-访问控制",
    ),
    BaselineCheckItem(
        id="L-AUDIT-01", category="安全审计", title="审计服务状态",
        description="检查auditd审计服务是否启用",
        check_command="systemctl is-active auditd 2>/dev/null || service auditd status 2>/dev/null | head -1",
        expected="contains:active", severity="high",
        remediation="执行 systemctl enable auditd && systemctl start auditd",
        standard="等保2.0-三级-安全审计",
    ),
    BaselineCheckItem(
        id="L-AUDIT-02", category="安全审计", title="Syslog服务状态",
        description="检查日志服务是否正常运行",
        check_command="systemctl is-active rsyslog 2>/dev/null || systemctl is-active syslog-ng 2>/dev/null",
        expected="contains:active", severity="high",
        remediation="执行 systemctl enable rsyslog && systemctl start rsyslog",
        standard="等保2.0-三级-安全审计",
    ),
    BaselineCheckItem(
        id="L-AUDIT-03", category="安全审计", title="历史命令记录",
        description="检查bash历史记录是否配置保留",
        check_command="echo $HISTSIZE",
        expected=">=1000", severity="low",
        remediation="在 /etc/profile 中设置 HISTSIZE=10000",
        standard="等保2.0-三级-安全审计",
    ),
    BaselineCheckItem(
        id="L-NET-01", category="网络安全", title="防火墙状态",
        description="检查系统防火墙是否启用",
        check_command="systemctl is-active firewalld 2>/dev/null || iptables -L -n 2>/dev/null | wc -l",
        expected="not_equals:0", severity="high",
        remediation="启用firewalld或配置iptables规则",
        standard="等保2.0-三级-网络安全",
    ),
    BaselineCheckItem(
        id="L-NET-02", category="网络安全", title="SSH端口",
        description="检查SSH是否使用非默认端口",
        check_command="grep '^Port' /etc/ssh/sshd_config | awk '{print $2}'",
        expected="not_equals:22", severity="low",
        remediation="修改SSH端口为非标准端口(建议10000以上)",
        standard="等保2.0-三级-网络安全",
    ),
    BaselineCheckItem(
        id="L-NET-03", category="网络安全", title="ICMP重定向",
        description="检查是否禁用ICMP重定向",
        check_command="sysctl net.ipv4.conf.all.accept_redirects 2>/dev/null | awk '{print $3}'",
        expected="equals:0", severity="medium",
        remediation="执行 sysctl -w net.ipv4.conf.all.accept_redirects=0",
        standard="等保2.0-三级-网络安全",
    ),
]

# ─── Windows 基线 ──────────────────────────────────────

WINDOWS_BASELINE_DENGBAO3 = [
    BaselineCheckItem(
        id="W-AUTH-01", category="身份鉴别", title="密码最小长度",
        description="检查Windows密码策略最小长度>=8",
        check_command="net accounts | findstr /i \"Minimum password length\"",
        expected=">=8", severity="high",
        remediation="本地安全策略 → 账户策略 → 密码策略 → 密码最小长度设为8",
        standard="等保2.0-三级-身份鉴别",
    ),
    BaselineCheckItem(
        id="W-AUTH-02", category="身份鉴别", title="账户锁定阈值",
        description="检查登录失败锁定次数是否<=5",
        check_command="net accounts | findstr /i \"Lockout threshold\"",
        expected="<=5", severity="high",
        remediation="本地安全策略 → 账户策略 → 账户锁定策略 → 锁定阈值设为5",
        standard="等保2.0-三级-身份鉴别",
    ),
    BaselineCheckItem(
        id="W-AUTH-03", category="身份鉴别", title="密码复杂性要求",
        description="检查是否启用密码复杂性要求",
        check_command="secedit /export /cfg C:\\secpol.cfg >nul && findstr \"PasswordComplexity\" C:\\secpol.cfg",
        expected="contains:1", severity="high",
        remediation="本地安全策略 → 账户策略 → 密码策略 → 启用密码必须符合复杂性要求",
        standard="等保2.0-三级-身份鉴别",
    ),
    BaselineCheckItem(
        id="W-AUDIT-01", category="安全审计", title="审核策略-登录事件",
        description="检查是否审核登录成功和失败事件",
        check_command="auditpol /get /category:\"Logon/Logoff\" | findstr /i \"Logon\"",
        expected="contains:Success and Failure", severity="high",
        remediation="本地安全策略 → 本地策略 → 审核策略 → 审核登录事件设为成功和失败",
        standard="等保2.0-三级-安全审计",
    ),
    BaselineCheckItem(
        id="W-ACCESS-01", category="访问控制", title="Guest账户状态",
        description="检查Guest账户是否已禁用",
        check_command="net user Guest | findstr /i \"active\"",
        expected="contains:No", severity="high",
        remediation="执行 net user Guest /active:no",
        standard="等保2.0-三级-访问控制",
    ),
    BaselineCheckItem(
        id="W-ACCESS-02", category="访问控制", title="远程桌面NLA",
        description="检查远程桌面是否启用网络级别身份验证",
        check_command="reg query \"HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp\" /v UserAuthentication",
        expected="contains:0x1", severity="medium",
        remediation="系统属性 → 远程 → 勾选仅允许运行使用网络级别身份验证的远程桌面的计算机连接",
        standard="等保2.0-三级-访问控制",
    ),
]

# ─── MySQL 基线 ────────────────────────────────────────

MYSQL_BASELINE = [
    BaselineCheckItem(
        id="M-AUTH-01", category="身份鉴别", title="root远程访问",
        description="检查MySQL root账户是否允许远程登录",
        check_command="mysql -e \"SELECT host FROM mysql.user WHERE user='root';\" 2>/dev/null",
        expected="not_contains:%", severity="critical",
        remediation="执行 DELETE FROM mysql.user WHERE user='root' AND host='%'; FLUSH PRIVILEGES;",
        standard="数据库安全基线",
    ),
    BaselineCheckItem(
        id="M-AUTH-02", category="身份鉴别", title="空密码账户",
        description="检查是否存在空密码的数据库账户",
        check_command="mysql -e \"SELECT user,host FROM mysql.user WHERE authentication_string='' OR authentication_string IS NULL;\" 2>/dev/null",
        expected="empty", severity="critical",
        remediation="为所有空密码账户设置强密码或删除无用账户",
        standard="数据库安全基线",
    ),
    BaselineCheckItem(
        id="M-NET-01", category="网络安全", title="监听地址",
        description="检查MySQL是否仅监听本地地址",
        check_command="grep 'bind-address' /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null || grep 'bind-address' /etc/my.cnf 2>/dev/null",
        expected="contains:127.0.0.1", severity="high",
        remediation="在my.cnf中设置 bind-address = 127.0.0.1",
        standard="数据库安全基线",
    ),
    BaselineCheckItem(
        id="M-AUDIT-01", category="安全审计", title="general_log",
        description="检查是否开启操作日志记录",
        check_command="mysql -e \"SHOW VARIABLES LIKE 'general_log';\" 2>/dev/null",
        expected="contains:ON", severity="medium",
        remediation="在my.cnf中设置 general_log = ON",
        standard="数据库安全基线",
    ),
]

# ─── Redis 基线 ────────────────────────────────────────

REDIS_BASELINE = [
    BaselineCheckItem(
        id="R-AUTH-01", category="身份鉴别", title="requirepass配置",
        description="检查Redis是否设置了访问密码",
        check_command="redis-cli CONFIG GET requirepass 2>/dev/null | tail -1",
        expected="not_empty", severity="critical",
        remediation="在redis.conf中设置 requirepass <强密码>",
        standard="数据库安全基线",
    ),
    BaselineCheckItem(
        id="R-NET-01", category="网络安全", title="bind地址",
        description="检查Redis是否绑定到本地地址",
        check_command="redis-cli CONFIG GET bind 2>/dev/null | tail -1",
        expected="contains:127.0.0.1", severity="critical",
        remediation="在redis.conf中设置 bind 127.0.0.1",
        standard="数据库安全基线",
    ),
    BaselineCheckItem(
        id="R-NET-02", category="网络安全", title="protected-mode",
        description="检查是否开启保护模式",
        check_command="redis-cli CONFIG GET protected-mode 2>/dev/null | tail -1",
        expected="equals:yes", severity="high",
        remediation="在redis.conf中设置 protected-mode yes",
        standard="数据库安全基线",
    ),
    BaselineCheckItem(
        id="R-ACCESS-01", category="访问控制", title="危险命令禁用",
        description="检查是否禁用了FLUSHALL等危险命令",
        check_command="redis-cli CONFIG GET rename-command 2>/dev/null",
        expected="not_empty", severity="high",
        remediation="在redis.conf中使用 rename-command FLUSHALL \"\" 禁用危险命令",
        standard="数据库安全基线",
    ),
]

ALL_BASELINES = {
    "linux_dengbao3": {"name": "等保三级-Linux主机基线", "items": LINUX_BASELINE_DENGBAO3},
    "windows_dengbao3": {"name": "等保三级-Windows主机基线", "items": WINDOWS_BASELINE_DENGBAO3},
    "mysql": {"name": "MySQL数据库安全基线", "items": MYSQL_BASELINE},
    "redis": {"name": "Redis数据库安全基线", "items": REDIS_BASELINE},
}


def evaluate_check(item: BaselineCheckItem, actual_output: str) -> BaselineCheckResult:
    actual = actual_output.strip()
    expected = item.expected
    passed = False

    if expected.startswith(">="):
        try:
            passed = int(actual) >= int(expected[2:])
        except ValueError:
            passed = False
    elif expected.startswith("<="):
        try:
            passed = int(actual) <= int(expected[2:])
        except ValueError:
            passed = False
    elif expected.startswith("equals:"):
        passed = actual.lower() == expected[7:].lower()
    elif expected.startswith("not_equals:"):
        passed = actual.lower() != expected[11:].lower()
    elif expected.startswith("contains:"):
        passed = expected[9:].lower() in actual.lower()
    elif expected.startswith("not_contains:"):
        passed = expected[13:].lower() not in actual.lower()
    elif expected == "not_empty":
        passed = len(actual) > 0
    elif expected == "empty":
        passed = len(actual) == 0

    return BaselineCheckResult(
        item=item, passed=passed, actual_value=actual,
        detail=f"期望: {expected}, 实际: {actual}" if not passed else "合规",
    )
