# RedScope

**渗透测试一体化工作台** — 从资产发现到漏洞利用到报告输出，覆盖渗透测试和安服工作的完整生命周期。

> **声明：本工具仅限已获书面授权的安全测试使用。未经授权对他人系统进行测试属违法行为。**

## 架构

```
用户 → 前端(3000) → Nginx → Backend(8000) → Scan Runner(9090) → Docker daemon
                                ↕                    ↕
                            PostgreSQL             docker.sock
                              Redis
                              Celery

安全隔离：
  Backend 永远碰不到 Docker daemon
  Scan Runner 是唯一有权操作 Docker 的进程
  Backend 被攻破不会导致宿主机失陷
```

## 功能概览

### 核心渗透测试

| 模块 | 能力 |
|------|------|
| **项目管理** | 实战/靶场/研究三种模式，多租户隔离，项目克隆，项目模板 |
| **边界管理** | 白名单/黑名单，越界阻断，授权过期检查，云厂商报备提醒，研究模式禁公网 |
| **资产测绘** | 子域名发现，端口扫描，指纹识别，API发现，CSV/Nessus导入 |
| **漏洞扫描** | 8种工具插件化（Nmap/Nuclei/Subfinder/Httpx/SQLMap/Dirsearch/Afrog/Fscan），隔离式执行，多引擎编排，DAG流水线 |
| **漏洞管理** | 详情抽屉，批量操作，筛选器，软删除，多引擎共识评分，风险接受函 |
| **手工测试** | 4套内置Checklist，Payload武器库，测试笔记，协同防撞车 |
| **报告生成** | Word报告自动生成，AI辅助写作，AI修复路线图，合规标准对标 |

### AI 能力（配置 LLM_API_KEY 即可用）

| 功能 | 说明 |
|------|------|
| **AI 安全对话** | 聊天式安全顾问，可关联项目上下文 |
| **智能扫描推荐** | 根据资产指纹推荐工具和 Nuclei 模板 |
| **攻击路径推导** | 从漏洞+已控主机推导攻击链，自动存入 AttackChain 表 |
| **自然语言查询** | 中文查数据（如「所有未修复的严重漏洞」） |
| **AI 报告总结** | 自动生成渗透测试报告总结章节 |
| **AI 修复路线图** | 本周/本月/季度分级修复建议 |
| **LLM 安全测试** | OWASP LLM Top 10 自动化测试 |
| **Session 摘要** | 工作 Session 结束时 AI 自动生成日报 |

### 作战管理

| 模块 | 能力 |
|------|------|
| **代理隧道** | 代理节点管理，链式代理，自动路由，隧道命令生成器 |
| **凭据管理** | 多类型凭据加密存储（PBKDF2+Fernet），密码复用检测 |
| **Shell 管理** | 已控主机看板，权限跟踪 |
| **攻击时间线** | 自动记录+手动打点，ATT&CK 自动映射，热力图 |
| **战后清理** | 自动生成清理清单，逐项勾选确认 |
| **工作 Session** | 按时段记录扫描/测试/截图，AI 生成日报摘要 |
| **截图管理** | 拖拽上传，自动关联漏洞/资产/Session |
| **终端录制** | 记录命令序列，保存为可复用 Playbook |

### 协同与运维

| 模块 | 能力 |
|------|------|
| **红蓝对抗** | 护网计分板，攻防得分，实时排名 |
| **工单审批** | 创建→审批→执行→复核→结项全流程 |
| **多租户** | 租户隔离（Project.tenant_id），用户上限控制 |
| **客户门户** | 独立登录，查看漏洞（隐藏攻击细节），申请复测，风险接受 |
| **漏洞情报** | NVD/CNVD 多源聚合，手动触发抓取，武器化阶段追踪 |
| **基线合规** | 等保三级 29 项检查模板，可选目标主机执行 |
| **用户管理** | 管理员角色/禁用，个人设置，修改密码 |
| **通知告警** | 企业微信/钉钉/飞书/Slack/Telegram Webhook，严重漏洞即时推送 |
| **网络拓扑** | ECharts 力导向图，可视化攻击路径 |
| **全局搜索** | 项目/漏洞/资产/情报四维度实时搜索 |
| **Prometheus** | /metrics 端点，可接入 Grafana 监控 |

## 安全特性

| 层面 | 措施 |
|------|------|
| **架构隔离** | Scan Runner 独立服务，Backend 零 Docker 导入，docker.sock 仅 Runner 可见 |
| **认证** | JWT + 密码强度校验，WebSocket 路径前缀校验，多租户 token |
| **授权** | RBAC 四级角色（admin/leader/engineer/viewer），项目归属+租户校验 |
| **输入净化** | 目标白名单正则+危险字符黑名单，subprocess_exec 列表参数 |
| **数据加密** | 凭据/代理密码 PBKDF2+Fernet 加密，100K 迭代 |
| **XXE 防护** | XML 解析使用安全 XMLParser |
| **SSRF 防护** | 内网地址过滤（10.x/172.16.x/192.168.x/127.x/169.254.x） |
| **LLM 安全** | AI 查询字段白名单+操作符白名单，防 prompt injection |
| **客户隔离** | 客户门户 token 绑定 project_id + is_active 检查 |
| **扫描安全** | 镜像精确白名单（8 个），并发信号量+计数双重限制 |
| **配置安全** | 生产环境强制 SECRET_KEY>=32 位，开发密钥打印警告 |
| **运行时** | 非 root 容器（backend+scanner），read-only+cap-drop=ALL，三级限流 |
| **审计** | 操作审计落库（AuditLog 表），error_id 追踪 |
| **网络** | Nginx HSTS+CSP（无 unsafe-eval）+X-Frame-Options，端口绑定 127.0.0.1 |
| **软删除** | Project/Asset/Finding 支持软删除（deleted_at），统计自动排除 |
| **分页保护** | page_size 上限 100，防 OOM |

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 磁盘空间 >= 10GB
- 内存 >= 4GB

### 一键启动

```bash
# 1. 克隆项目
git clone https://github.com/jovian-zhibai/RedScope.git
cd RedScope

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 SECRET_KEY、DB_PASSWORD 等
# SECRET_KEY 生成: python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 3. 启动（后端会自动运行数据库迁移）
docker compose up -d --build

# 4. 打开浏览器
# 访问 http://localhost:3000
# 首次使用请注册账号
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:3000 |
| API 文档 | http://localhost:8000/docs |
| 客户门户 | http://localhost:3000/portal |
| Prometheus | http://localhost:8000/metrics |

## 项目结构

```
redscope/
├── backend/                        # 后端 (Python 3.12 + FastAPI)
│   ├── main.py                     # 入口，20个API路由 + 4层中间件 + 全局搜索
│   ├── config.py                   # 配置管理（CORS环境变量化，密钥强度校验）
│   ├── database.py                 # 异步数据库连接
│   ├── database_sync.py            # 同步数据库连接（Celery 共用）
│   ├── api/                        # 20个API模块
│   │   ├── auth.py                 #   注册/登录/改密/用户管理/项目克隆
│   │   ├── projects.py             #   项目CRUD（租户隔离，N+1优化）
│   │   ├── sessions.py             #   工作Session/截图/录制/模板/风险接受
│   │   ├── wiring.py               #   核心能力（匹配/去重/评分/OPSEC/AI接口）
│   │   └── ...
│   ├── core/                       # 核心模块
│   │   ├── rbac.py                 #   角色权限 + 项目归属 + 租户校验
│   │   ├── ssrf_filter.py          #   SSRF 内网地址过滤
│   │   ├── pipeline_executor.py    #   DAG 流水线（含环检测）
│   │   └── ...
│   ├── ai/                         # AI 能力
│   │   ├── assistant.py            #   安全对话/扫描推荐/攻击路径/自然语言查询
│   │   ├── report_writer.py        #   AI 报告写作
│   │   └── llm_security_test.py    #   LLM OWASP Top 10 测试
│   ├── models/                     # 12个模型文件，40+张表
│   ├── tasks/                      # Celery 异步任务
│   ├── parsers/                    # 8种工具解析器
│   ├── tests/                      # pytest 测试
│   └── migrations/                 # Alembic 数据库迁移
├── scan-runner/                    # 扫描执行服务（唯一有 Docker 权限）
├── frontend/                       # 前端 (Vue 3 + Element Plus)
│   └── src/
│       ├── views/                  # 22个页面
│       ├── components/             # ECharts 拓扑/终端/边界管理
│       ├── __tests__/              # vitest 测试
│       └── router/                 # 路由守卫（JWT过期检查）
├── plugins/builtin/                # 8个预置工具插件
├── pipelines/                      # 3套扫描流水线预设
├── docker/
│   ├── Dockerfile.backend          # 多阶段构建，非root，entrypoint自动迁移
│   ├── Dockerfile.scanner          # 非root
│   ├── nginx.conf                  # HSTS + CSP + /metrics 代理
│   ├── entrypoint.sh               # 启动前自动 alembic upgrade
│   └── build_offline_package.sh    # 离线部署包（含10个镜像）
├── scripts/
│   ├── backup.sh                   # PostgreSQL 自动备份（保留30份）
│   ├── restore.sh                  # 数据库恢复
│   └── cleanup_scan_output.sh      # 扫描产出自动清理
├── docker-compose.yml              # 6个服务编排
├── alembic.ini                     # 数据库迁移配置
├── Makefile                        # make setup/dev/test/migrate/backup
└── .env.example
```

## 技术栈

| 层面 | 技术 |
|------|------|
| 后端框架 | Python 3.12 + FastAPI |
| 数据库 | PostgreSQL 16 + Alembic 迁移 |
| 缓存/队列 | Redis 7 + Celery |
| 前端框架 | Vue 3 + Element Plus + ECharts |
| 终端模拟 | @xterm/xterm + WebSocket |
| 报告生成 | python-docx + WeasyPrint |
| 凭据加密 | cryptography (PBKDF2 + Fernet) |
| AI 能力 | DeepSeek / 通义千问 / OpenAI 兼容接口 |
| 可观测性 | Prometheus + 结构化日志 |
| 测试 | pytest + vitest |
| 容器化 | Docker（多阶段构建）+ Docker Compose |

## 开发

```bash
# 使用 Makefile（推荐）
make setup       # 安装全部依赖
make dev          # 启动本地开发（前后端）
make test         # 运行全部测试
make migrate msg="add xxx"  # 创建数据库迁移

# 或手动
cd backend && pip install -r requirements.txt && uvicorn backend.main:app --reload --port 8000
cd frontend && npm install && npm run dev
celery -A backend.tasks.celery_app worker -l info
```

## 数据库备份

```bash
# 自动备份（建议加入 crontab）
bash scripts/backup.sh ./backups

# 恢复
bash scripts/restore.sh backups/redscope_20260625_030000.sql.gz
```

## API 版本

所有 API 端点使用 `/api/v1/` 前缀。Swagger 文档: http://localhost:8000/docs

## 添加自定义扫描工具

在 `plugins/custom/` 目录下创建 YAML 文件：

```yaml
plugin:
  name: my-tool
  display_name: "我的工具"
  category: vuln_scan
  docker:
    image: "my-tool:latest"
  inputs:
    - name: target
      type: string
      required: true
  command: "my-tool scan {target} -o /output/result.json"
  output:
    format: json
    path: "/output/result.json"
```

在工具管理页面点击"重新加载"即可使用。新镜像需添加到 `docker-compose.yml` 的 `ALLOWED_IMAGES` 白名单。

## 离线部署

```bash
# 在有网环境生成离线包（含全部 10 个扫描工具镜像）
bash docker/build_offline_package.sh

# 输出: redscope-offline-YYYYMMDD.tar.gz
# 拷贝到U盘，在目标机器上：
tar -xzf redscope-offline-*.tar.gz && cd redscope-offline-*/ && bash install.sh
```

## License

Apache License 2.0 — 附中英文免责声明，详见 [LICENSE](LICENSE)。
