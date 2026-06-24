# Changelog

## v1.0.0 (2026-06-24)

首个发布版本。

### 核心功能
- 项目管理：实战/靶场/研究三种模式，项目归属隔离
- 边界管理：白名单/黑名单/越界阻断/云厂商报备/紧急停止
- 资产测绘：子域名/端口/指纹识别
- 漏洞扫描：8种工具插件化(nmap/nuclei/subfinder/httpx/sqlmap/dirsearch/afrog/fscan)
- 漏洞情报：NVD/CNVD多源聚合
- 智能关联：指纹→漏洞被动匹配、攻击链推演、综合风险评分、结果去重
- 手工测试：4套逻辑漏洞Checklist、Payload武器库、协同防撞车
- AI安全测试：LLM Prompt注入/数据泄露/越权测试(OWASP LLM Top 10)
- 代理隧道：节点管理/链式代理/自动路由/隧道命令生成
- 凭据管理：多类型凭据 Fernet 加密存储
- Shell管理：已控主机看板/权限跟踪
- 攻击时间线：自动记录+ATT&CK自动映射+热力图
- 战后清理：自动清理清单生成
- 报告生成：Word报告+LLM辅助写作
- 基线合规：等保三级Linux/Windows/MySQL/Redis基线(29项)
- 红蓝对抗：护网计分板
- 工单审批：全流程工单流转(manager+权限)
- 多租户：租户隔离(admin权限)
- 客户门户：客户独立登录/查看漏洞/申请复测(IDOR防护)
- 集成终端：Web终端(JWT鉴权)
- 通知告警：企业微信/钉钉/飞书
- 导入导出：CSV/Nessus导入、漏洞CSV导出、项目归档
- 流水线编排：DAG扫描流水线+3套预设
- 离线部署：一键打包离线安装

### 安全架构
- Scan Runner 独立服务：Backend 零 Docker 权限，扫描通过 HTTP API 委托给隔离的 Runner
- JWT 认证 + RBAC 四级角色(admin/manager/engineer/viewer)
- 项目归属校验：66个路由全覆盖，创建者私有+admin放行
- 输入净化：白名单正则+危险字符拦截，subprocess_exec 列表参数
- 凭据加密：Fernet 加密存储，API 返回固定掩码
- Docker 安全：非root运行、read-only+cap-drop=ALL、镜像精确白名单、并发信号量
- 限流：三级(登录10/分、扫描20/分、通用200/分)
- 审计日志：POST/PUT/DELETE 全记录，按路径分级
- 前端守卫：路由级 JWT 过期检查
- Nginx 安全头：CSP/X-Frame-Options/X-Content-Type-Options/server_tokens off
- 配置安全：生产环境强制 SECRET_KEY>=32位、禁止默认值

### 技术栈
- 后端：Python 3.12 + FastAPI + SQLAlchemy + Celery
- 前端：Vue 3 + Element Plus + xterm.js
- 数据库：PostgreSQL 16 + Redis 7
- 扫描隔离：独立 Scan Runner + Docker SDK
- 部署：Docker Compose (6个服务)
