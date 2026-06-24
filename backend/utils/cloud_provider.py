"""Cloud provider detection: identifies which cloud provider an IP belongs to."""

# Major Chinese and international cloud provider IP ranges (representative samples)
# In production, use a full IP database like ip2region or MaxMind

CLOUD_PROVIDERS = {
    "阿里云": {
        "cidr_prefixes": ["47.92.", "47.93.", "47.94.", "47.95.", "47.96.", "47.97.", "47.98.", "47.99.",
                          "47.100.", "47.101.", "47.102.", "47.103.", "47.104.", "47.105.",
                          "39.96.", "39.97.", "39.98.", "39.99.", "39.100.", "39.101.",
                          "121.40.", "121.41.", "121.42.", "121.43.",
                          "120.24.", "120.25.", "120.26.", "120.27.",
                          "112.124.", "114.55.", "115.28.", "115.29."],
        "pentest_url": "https://yundun.console.aliyun.com/?p=sc#/sc/apply",
        "notice": "阿里云要求提前提交渗透测试申请，否则可能触发安全告警并封禁IP",
    },
    "腾讯云": {
        "cidr_prefixes": ["119.29.", "122.51.", "82.157.", "43.128.", "43.129.", "43.130.",
                          "1.12.", "1.13.", "1.14.", "1.15.", "106.52.", "106.53.", "106.54.", "106.55.",
                          "118.24.", "118.25.", "118.89.", "129.28.", "129.204."],
        "pentest_url": "https://console.cloud.tencent.com/security/pentest",
        "notice": "腾讯云要求在安全中心提交渗透测试授权申请",
    },
    "华为云": {
        "cidr_prefixes": ["114.116.", "121.36.", "121.37.", "122.112.", "123.60.",
                          "124.70.", "124.71.", "139.9.", "139.159."],
        "pentest_url": "https://console.huaweicloud.com/ticket/",
        "notice": "华为云需通过工单系统提交渗透测试报备",
    },
    "AWS": {
        "cidr_prefixes": ["3.0.", "3.1.", "13.112.", "13.113.", "13.124.", "13.125.",
                          "13.210.", "13.211.", "13.228.", "13.229.", "13.230.", "13.231.",
                          "18.136.", "18.162.", "18.163.", "52.76.", "52.77.", "54.169.", "54.179.", "54.222.", "54.223."],
        "pentest_url": "https://aws.amazon.com/security/penetration-testing/",
        "notice": "AWS允许对自有资源进行渗透测试,但部分服务有限制,建议查看官方政策",
    },
}


def detect_cloud_provider(ip: str) -> dict | None:
    for provider, info in CLOUD_PROVIDERS.items():
        for prefix in info["cidr_prefixes"]:
            if ip.startswith(prefix):
                return {
                    "provider": provider,
                    "pentest_url": info["pentest_url"],
                    "notice": info["notice"],
                }
    return None


def check_cloud_compliance(targets: list[str]) -> list[dict]:
    warnings = []
    seen_providers = set()
    for target in targets:
        result = detect_cloud_provider(target)
        if result and result["provider"] not in seen_providers:
            seen_providers.add(result["provider"])
            warnings.append({
                "target": target,
                "provider": result["provider"],
                "pentest_url": result["pentest_url"],
                "notice": result["notice"],
            })
    return warnings
