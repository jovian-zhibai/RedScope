"""Input sanitizer: validates and sanitizes user inputs to prevent injection."""

import re
import shlex


SAFE_TARGET_PATTERN = re.compile(r'^[a-zA-Z0-9\.\-\:\/\[\]\_\%]+$')
DANGEROUS_CHARS = set(';|&$`(){}!><\n\r')


def sanitize_target(target: str) -> str:
    target = target.strip()
    if not target:
        raise ValueError("目标不能为空")
    if len(target) > 512:
        raise ValueError("目标长度超过限制")
    if any(c in target for c in DANGEROUS_CHARS):
        raise ValueError(f"目标包含非法字符: {target}")
    if not SAFE_TARGET_PATTERN.match(target):
        raise ValueError(f"目标格式不合法: {target}")
    return target


def sanitize_targets(targets: list[str]) -> list[str]:
    return [sanitize_target(t) for t in targets]


def safe_shell_split(cmd: str) -> list[str]:
    return shlex.split(cmd)
