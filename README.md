# RedScope

**渗透测试一体化工作台** — 从资产发现到漏洞利用到报告输出，覆盖渗透测试和安服工作的完整生命周期。

> **声明：本工具仅限已获书面授权的安全测试使用。未经授权对他人系统进行测试属违法行为。**

## 架构

```
用户 → 前端(3000) → Nginx → Backend(8000) → Scan Runner(9090) → Docker daemon
                                  ↕                    ↕
                              PostgreSQL             docker.sock
                                Redis

安全隔离：
  Backend 永远碰不到 Docker daemon
  Scan Runner 是唯一有权操作 Docker 的进程
  Backend 被攻破不会导致宿主机失陷
```

## 功能概览

| 模块 | 能力 |
|------|------|
| **项目管理** | 实战/靶场/研究三种模式，项目归属隔离（创建者私有） |
| **边界管理** | 白名单/黑名单，越界阻断，授权过期检查，云厂商报备提醒，紧急停止 |
| **资产测绘** | 子域名发现，端口扫描，指纹识别，API发现，被动分析 |
| **漏洞扫描** | 8种工具插件化，隔离式 Scan Runner 执行，多引擎编排，流水线 |
| **漏洞情报** | NVD/CNVD多源聚合，武器化阶段追踪，PoC管理，误报标记 |
| **智能关联** | 指纹→版本→漏洞被动匹配，攻击链推演，综合风险评分，结果去重 |
| **手工测试** | 逻辑漏洞Checklist(4套内置)，Payload武器库，协同防撞车 |
| **AI安全测试** | LLM Prompt注入/数据泄露/越权测试，对标OWASP LLM Top 10 |
| **代理隧道** | 代理节点管理，链式代理，自动路由，隧道命令生成器，健康监控 |
| **凭据管理** | 多类型凭据加密存储（Fernet），密码复用检测 |
| **Shell管理** | 已控主机看板，权限跟踪，上传文件记录 |
| **攻击时间线** | 自动记录+手动打点，MITRE ATT&CK自动映射，热力图 |
| **战后清理** | 自动生成清理清单，逐项勾选确认 |
| **报告生成** | Word报告自动生成，LLM辅助写作，合规标准对标 |
| **基线合规** | 等保三级Linux/Windows/MySQL/Redis基线检查，29项模板 |
| **红蓝对抗** | 护网计分板，攻防得分，预设评分规则 |
| **工单审批** | 创建→审批→执行→复核→结项全流程（manager+权限） |
| **多租户** | 租户隔离，用户上限控制（admin权限） |
| **客户门户** | 客户独立登录，查看漏洞（隐藏攻击细节），申请复测 |
| **集成终端** | Web终端(JWT鉴权)，Ctrl+\` 快捷唤起 |
| **通知告警** | 企业微信/钉钉/飞书 Webhook 推送 |
| **导入导出** | CSV资产/Nessus报告导入，漏洞CSV导出，项目归档 |
| **离线部署** | 一键打包所有镜像+数据，U盘拷到内网部署 |

## 安全特性

| 层面 | 措施 |
|------|------|
| **架构隔离** | Scan Runner 独立服务，Backend 零 Docker 导入，docker.sock 仅 Runner 可见 |
| **认证** | JWT + 密码强度校验(>=8位,字母+数字)，WebSocket 连接前验证 token |
| **授权** | RBAC 四级角色(admin/manager/engineer/viewer)，项目归属校验(66个接入点) |
| **输入净化** | 目标白名单正则+危险字符黑名单，subprocess_exec 列表参数(永不 shell=True) |
| **数据加密** | 凭据/代理密码 Fernet 加密存储，列表返回固定掩码 |
| **客户隔离** | 客户门户 token 绑定 project_id，IDOR 防护 |
| **扫描安全** | 镜像精确白名单，并发上限(信号量+计数双重)，挂载路径白名单 |
| **配置安全** | 生产环境强制 SECRET_KEY>=32位，禁止默认值，自动关闭 debug |
| **运行时** | 非 root 容器，read-only + cap-drop=ALL，限流(三级)，审计日志 |
| **网络** | Nginx 安全头(CSP/X-Frame/HSTS)，端口绑定 127.0.0.1，前端路由守卫 |

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 磁盘空间 >= 10GB
- 内存 >= 4GB

### 一键启动

```bash
# 1. 克隆项目
git clone https://github.com/yourname/redscope.git
cd redscope

# 2. 配置环境变量（必须修改密码和密钥）
cp .env.example .env
# 编辑 .env，设置 SECRET_KEY、DB_PASSWORD、REDIS_PASSWORD、RUNNER_SECRET
# SECRET_KEY 生成: python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 3. 启动
docker-compose up -d --build

# 4. 打开浏览器
# 访问 http://localhost:3000
# 首次使用请注册账号
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:3000 |
| 后端API | http://localhost:8000 |
| API文档 | http://localhost:8000/docs |

## 项目结构

```
redscope/
├── backend/                        # 后端 (Python + FastAPI)
│   ├── main.py                     # 入口，19个API路由 + 4层中间件
│   ├── config.py                   # 配置管理（生产环境强制校验）
│   ├── database.py                 # 异步数据库连接
│   ├── database_sync.py            # 同步数据库连接（Celery/批处理共用）
│   ├── api/                        # 19个API模块
│   ├── core/                       # 核心业务模块
│   │   ├── auth_middleware.py      #   JWT认证中间件
│   │   ├── rbac.py                 #   角色权限 + 项目归属校验
│   │   ├── rate_limiter.py         #   三级限流
│   │   ├── audit_logger.py         #   操作审计
│   │   ├── error_handler.py        #   全局异常处理 + 结构化日志
│   │   ├── boundary_checker.py     #   边界检查器
│   │   ├── engine_orchestrator.py  #   引擎编排器（通过HTTP调scan-runner）
│   │   ├── plugin_manager.py       #   插件管理器
│   │   └── ...                     #   漏洞匹配/去重/评分/ATT&CK/通知等
│   ├── utils/
│   │   ├── sanitizer.py            #   输入净化
│   │   ├── crypto.py               #   凭据加密
│   │   └── cloud_provider.py       #   云厂商识别
│   ├── models/                     # 12个模型文件，35+张表
│   ├── tasks/                      # Celery异步任务
│   ├── ai/                         # LLM集成
│   ├── intel/                      # 漏洞情报爬虫
│   └── parsers/                    # 扫描结果解析器（6种工具）
├── scan-runner/                    # 扫描执行服务（唯一有Docker权限的进程）
│   ├── main.py                     # FastAPI，镜像白名单+并发限制+信号量
│   └── requirements.txt
├── frontend/                       # 前端 (Vue 3 + Element Plus)
│   └── src/
│       ├── views/                  # 13个页面
│       ├── components/             # 终端/拓扑/边界管理组件
│       └── router/                 # 路由守卫（JWT过期检查）
├── plugins/builtin/                # 8个预置工具插件
├── pipelines/                      # 3套扫描流水线预设
├── docker/
│   ├── Dockerfile.backend          # 非root运行
│   ├── Dockerfile.scanner          # Scan Runner镜像
│   ├── Dockerfile.frontend
│   ├── nginx.conf                  # 安全头 + 反向代理
│   └── build_offline_package.sh    # 离线部署包生成
├── docker-compose.yml              # 6个服务编排
├── .env.example
├── LICENSE                         # Apache 2.0 + 免责声明
└── CHANGELOG.md
```

## 技术栈

| 层面 | 技术 |
|------|------|
| 后端框架 | Python 3.12 + FastAPI |
| 数据库 | PostgreSQL 16 |
| 缓存/队列 | Redis 7 + Celery |
| 前端框架 | Vue 3 + Element Plus |
| 终端模拟 | xterm.js + WebSocket |
| 报告生成 | python-docx |
| 凭据加密 | cryptography (Fernet) |
| AI能力 | DeepSeek / Qwen / OpenAI兼容接口 |
| 扫描隔离 | 独立 Scan Runner 服务 + Docker SDK |
| 容器化 | Docker + Docker Compose |

## 配置说明

复制 `.env.example` 为 `.env`，**必须修改以下字段**：

```bash
# 运行环境（生产环境会强制校验密钥强度）
ENVIRONMENT=production

# 数据库密码
DB_PASSWORD=your_secure_password

# Redis密码
REDIS_PASSWORD=your_secure_password

# JWT密钥（必须 >= 32位随机字符串）
# 生成: python3 -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_KEY=your_random_secret_key

# Scan Runner 通信密钥
RUNNER_SECRET=your_random_runner_secret

# LLM API（可选，用于AI报告写作和LLM安全测试）
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# 通知Webhook（可选）
NOTIFY_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
NOTIFY_CHANNEL=wecom  # wecom / dingtalk / feishu
```

## 添加自定义扫描工具

在 `plugins/custom/` 目录下创建 YAML 文件：

```yaml
plugin:
  name: my-tool
  display_name: "我的工具"
  description: "自定义扫描工具"
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
  proxy:
    supported: true
    flag: "--proxy socks5://{proxy_url}"
```

在工具管理页面点击"重新加载"即可使用。新镜像需添加到 `docker-compose.yml` 的 `ALLOWED_IMAGES` 白名单。

## 离线部署

用于无法联网的内网环境：

```bash
# 在有网环境生成离线包
bash docker/build_offline_package.sh

# 输出: redscope-offline-YYYYMMDD.tar.gz
# 拷贝到U盘，在目标机器上：
tar -xzf redscope-offline-*.tar.gz
cd redscope-offline-*/
bash install.sh
```

## 开发

```bash
# 后端开发（不用Docker）
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# 前端开发
cd frontend
npm install
npm run dev

# 启动Celery Worker
celery -A backend.tasks.celery_app worker -l info

# 启动Scan Runner（本地开发需要Docker）
cd scan-runner
pip install -r requirements.txt
uvicorn main:app --port 9090
```

## API文档

启动后访问 http://localhost:8000/docs 查看 Swagger API 文档。

## License

Apache License 2.0 — 附中英文免责声明，详见 [LICENSE](LICENSE)。
