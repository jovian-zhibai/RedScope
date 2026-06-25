# RedScope 全量修复提示词（完整版）

> **使用说明**：将以下内容完整粘贴给 AI 编程助手（Cursor / GitHub Copilot / ChatGPT / Claude 等），作为系统级修复指令。
> 项目路径：`/mnt/local/RedScope`，技术栈：FastAPI(异步) + SQLAlchemy + Celery + Vue3 + Element Plus。

---

## 一、项目背景与修复范围

RedScope 是一个**渗透测试一体化工作台**，包含后端（`backend/`）和前端（`frontend/src/`）两部分。
本次审查覆盖了 **53 个源码文件**，发现 **52 个逻辑问题/Bug**，按严重程度分为 🔴严重、🟠高危、🟡中危 三档。
本提示词要求**全部修复**，不遗漏任何一项。

---

## 二、🔴 严重问题（必须立即修复，共 10 个）

### 【B-01】注册接口无速率限制保护 → 可被批量刷库
- **文件**: `backend/api/auth.py` 第 59-85 行 `/register` 端点
- **问题**: 注册接口完全没有 IP 级限流，攻击者可脚本批量创建账号
- **修复要求**:
  1. 在 `backend/core/rate_limiter.py` 中新增 `check_rate_limit(key, max_requests, window_seconds)` 方法
  2. 对 `/api/v1/auth/register` 施加严格限流：**同一 IP 每 3 次请求/每小时**
  3. 在 `auth_middleware.py` 或通过 FastAPI middleware 统一拦截注册请求的频率
  4. 考虑增加图形验证码或邮箱验证机制（可选增强）

### 【B-02】JWT 使用已废弃 API + 无 Refresh Token 机制
- **文件**: `backend/api/auth.py` 第 49 行
- **问题代码**:
  ```python
  to_encode["exp"] = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
  ```
- **修复要求**:
  1. 将 `datetime.utcnow()` 替换为 `datetime.now(timezone.utc)`（Python 3.12+ 兼容）
  2. 新增 Refresh Token 机制：
     - 登录时同时返回 `access_token`（有效期 30 分钟）和 `refresh_token`（有效期 7 天）
     - 新增 `POST /api/v1/auth/refresh` 端点，用 refresh_token 换取新 access_token
     - 新增 token 黑名单表（Redis 或数据库），支持主动撤销
  3. 在 `config.py` 中新增 `refresh_token_expire_days: int = 7` 配置项

### 【B-03】认证中间件路径白名单用精确匹配，可被绕过
- **文件**: `backend/core/auth_middleware.py` 第 9-22 行
- **问题代码**:
  ```python
  PUBLIC_PATHS = {
      "/api/health", "/api/v1/health",
      "/api/auth/login", "/api/v1/auth/login",
      # ...
  }
  # 使用 path in PUBLIC_PATHS 做精确匹配
  ```
- **修复要求**:
  1. 改为**前缀匹配**：检查 path 是否以某个公开路径开头
  2. 对于带路径参数的路由（如 `/reset/{token}`），使用正则或路由模式匹配
  3. 添加单元测试验证各种 URL 变体的匹配结果

### 【B-04】WebSocket 终端直接 fork /bin/bash — 无沙箱隔离
- **文件**: `backend/api/terminal.py` 第 41-52 行
- **问题代码**:
  ```python
  os.execvp("/bin/bash", ["/bin/bash", "--norc", "--noprofile"])
  ```
- **修复要求**:
  1. 将 `/bin/bash` 替换为 `rbash`（restricted bash）或自定义受限 shell
  2. 添加容器化隔离：每个 session 运行在独立的 namespace/chroot 中
  3. **添加命令审计日志**：记录用户执行的每条命令到数据库（含时间戳、用户ID、命令内容）
  4. `MAX_SESSIONS_PER_USER` 的限制改用 Redis 存储，支持多实例部署
  5. 添加危险命令黑名单检测（如 `rm -rf /`、`> /etc/passwd`、`curl | bash` 等），命中时拒绝执行并记录告警
  6. 进程清理增加僵尸进程检测和自动回收机制

### 【B-05】_run_local 命令注入风险
- **文件**: `backend/core/engine_orchestrator.py` 第 129-155 行
- **问题代码**:
  ```python
  args = shlex.split(full_cmd)
  process = await asyncio.create_subprocess_exec(*args, ...)
  ```
- **修复要求**:
  1. 对 `full_cmd` 做二次 sanitize 校验（即使经过 `sanitize_target`，plugin 的 command 模板仍可能引入风险字符）
  2. 禁止以下字符出现在最终命令中：`` $ ` ; | & > < ! \n \r `` 以及 null byte
  3. 记录每次本地执行的完整命令到审计日志
  4. 考虑废弃 `_run_local`，所有扫描强制走 Docker 容器执行

### 【B-06】SSRF 防护可被 DNS Rebinding 绕过
- **文件**: `backend/core/ssrf_filter.py` 第 21-41 行
- **问题代码**:
  ```python
  resolved = socket.getaddrinfo(hostname, None)
  for _, _, _, _, addr in resolved:
      ip = ipaddress.ip_address(addr[0])
      for network in BLOCKED_NETWORKS:
          if ip in network:
              raise HTTPException(...)
  # socket.gaierror 被 pass 吞掉
  ```
- **修复要求**:
  1. 实现 **DNS Rebinding 防御**：先解析做预检，然后在实际 HTTP 请求时绑定解析到的 IP 连接（使用 `httpx` 的参数绑定 resolved IP）
  2. 添加 IPv4-mapped IPv6 地址检查（`::ffff:127.0.0.1` 应视为 loopback）
  3. DNS 解析失败时（`gaierror`）应**拒绝请求**而非放行
  4. 添加超时控制，防止 DNS 解析被拖慢
  5. 考虑使用 `asyncio.getaddrinfo` 异步版本避免阻塞事件循环

### 【F-01】TerminalPanel WebSocket URL 构建断裂（致命 Bug）
- **文件**: `frontend/src/components/TerminalPanel.vue` 第 39 行
- **问题代码**:
  ```javascript
  ws = new WebSocket(`///ws/terminal/?token=`)  // 三斜杠！token 未插值！
  ```
- **修复要求**:
  ```javascript
  // 正确写法：
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${location.host}/ws/terminal/?token=${token}`)
  ```

### 【F-02】管理员权限依赖客户端 JWT 解析，可被伪造绕过
- **文件**: `frontend/src/views/Settings.vue` 第 163-170 行
- **问题代码**:
  ```javascript
  const isAdmin = computed(() => {
      const token = localStorage.getItem('token')
      if (!token) return false
      const payload = JSON.parse(atob(token.split('.')[1]))
      return payload.role === 'admin'
  })
  ```
- **修复要求**:
  1. 删除此客户端 JWT 解析逻辑
  2. 从 `GET /api/v1/auth/me` 接口返回的用户信息中获取 role 字段
  3. 将角色信息存储在 Pinia/Vuex store 中（如 `useUserStore().role`）
  4. 所有需要管理员权限的前端页面/组件都从 store 读取，而非本地计算
  5. 处理 `atob` 解码失败的情况（Unicode 字符等）

### 【F-03】NetworkTopology 模板字符串插值变量丢失
- **文件**: `frontend/src/components/NetworkTopology.vue` 第 53-59, 63-66 行
- **问题**: 模板字面量中的变量引用 `` `proxy_${...}` `` `` `${...}:${port}` `` 等被截断为空字符串
- **修复要求**:
  1. 补全所有丢失的模板插值变量（`p.id`, `p.name`, `p.port`, `h.id`, `h.hostname`, `h.ports` 等）
  2. 确保 nodes 和 edges 数组正确填充
  3. 验证 ECharts graph 渲染效果正常

### 【F-04】截图 view_url 直接 `<img :src>` 渲染，存在 XSS 风险
- **文件**: `Findings.vue` 第 114 行、`ProjectDetail.vue` 截图区域
- **问题代码**:
  ```html
  <img :src="s.view_url" />
  <img :src="s.view_url" @click="window.open(s.view_url, '_blank')" />
  ```
- **修复要求**:
  1. 前端对 view_url 做协议白名单校验：只允许 `http://`、`https://`、相对路径 `/`
  2. 后端 `sessions.py` 上传时增加 **magic bytes 文件头校验**（不只看扩展名）：
     - PNG: `\x89PNG\r\n\x1a\n`
     - JPEG: `\xff\xd8\xff`
     - GIF: `GIF87a` 或 `GIF89a`
     - WebP: `RIFF....WEBP`
  3. 文件返回时设置 `Content-Disposition: attachment` 或严格的 `Content-Type`
  4. `window.open` 改为新标签页中展示安全预览页，而非直接打开 URL

---

## 三、🟠 高危问题（必须修复，共 15 个）

### 【B-07】Pipeline DAG 多依赖节点 targets 被覆盖丢失（核心逻辑 Bug）
- **文件**: `backend/core/pipeline_executor.py` 第 37-40 行
- **问题代码**:
  ```python
  targets = initial_targets
  for dep_id in deps.get(node_id, []):
      if dep_id in completed:
          targets = completed[dep_id]  # ← 循环覆盖！只保留最后一个
  ```
- **修复要求**:
  ```python
  # 修复：合并所有依赖节点的输出
  targets = list(initial_targets)
  seen = set(targets)
  for dep_id in deps.get(node_id, []):
      if dep_id in completed:
          for t in completed[dep_id]:
              if t not in seen:
                  targets.append(t)
                  seen.add(t)
  ```

### 【B-08】去重引擎使用独立同步 Session，事务不一致
- **文件**: `backend/core/dedup.py` 第 14 行、`backend/api/wiring.py` 第 77-84 行
- **问题**: `dedup_findings` 接收同步 `Session`，但调用方创建独立 session 与 async session 无协调
- **修复要求**:
  1. 将 dedup 改为异步版本：`async def dedup_findings_async(db: AsyncSession, project_id: int)`
  2. 使用传入的 async session，不再创建独立 session
  3. 或者确保独立 session 的操作在同一个数据库事务边界内完成
  4. 在 `scan_worker.py` 中同步修改调用方式

### 【B-09】数据库连接池配置过高，多实例部署必耗尽
- **文件**: `backend/database.py` 第 7 行
- **问题代码**:
  ```python
  engine = create_async_engine(..., pool_size=20, max_overflow=10)  # 单进程 30 连接
  ```
- **修复要求**:
  1. 改为 `pool_size=5, max_overflow=2, pool_recycle=1800, pool_pre_ping=True`
  2. 在 `config.py` 中新增配置项：
     ```python
     db_pool_size: int = 5
     db_max_overflow: int = 2
     ```
  3. Celery worker 使用独立的连接池配置（更小的值）
  4. 在启动日志中打印实际连接池配置，便于运维排查

### 【B-10】全局搜索 API 权限过滤不完整
- **文件**: `backend/main.py` 第 108-156 行
- **问题**:
  1. Knowledge 表（漏洞情报）没有任何权限过滤
  2. 非 admin 时 `project_ids` 为空列表会导致 SQL `IN ()` 报错
  3. 路由缺少 RBAC 装饰器保护
- **修复要求**:
  1. Knowledge 表搜索也需要基于 tenant_id 过滤
  2. 当 `project_ids` 为空列表时，SQL 改为 `WHERE 1=0` 或跳过查询
  3. 添加 `RequireRole(["admin", "engineer", "viewer"])` 装饰器

### 【B-11】域名通配符匹配只能匹配一级子域
- **文件**: `backend/core/boundary_checker.py` 第 79-81 行
- **问题代码**:
  ```python
  pattern = rule.target_value.replace(".", r"\.").replace("*", r"[^.]*")
  # *.example.com → ^[^.]*\.example\.com  只能匹配 a.example.com
  ```
- **修复要求**:
  ```python
  if rule.target_type == "domain":
      pattern = rule.target_value.replace(".", r"\.").replace("*", r".*")
      return bool(re.match(f"^{pattern}$", target, re.IGNORECASE))
  ```
  注意区分 domain 类型用 `.*`（匹配多级子域）和其他类型的通配语义。

### 【B-12】密码策略过弱且 register/change_password 代码重复
- **文件**: `backend/api/auth.py` 第 61-64 行（register）、change_password 接口
- **修复要求**:
  1. 提取公共函数 `validate_password(password: str)`：
     - 最少 8 位
     - 必须包含字母 + 数字 + 特殊字符（至少一种：`!@#$%^&*`）
     - 不能全数字或全字母
     - 不能是常见弱密码（维护一个 TOP 100 弱密码黑名单）
     - 不能包含用户名或邮箱前缀
  2. register 和 change_password 都调用此函数
  3. 密码强度在前端也做同样校验（即时反馈）

### 【B-13】Rate Limiter 纯内存存储，多实例部署完全失效
- **文件**: `backend/core/rate_limiter.py` 第 8-21 行
- **修复要求**:
  1. 改用 Redis 存储计数（项目已有 `settings.redis_url`）：
     ```python
     key = f"rate_limit:{identifier}:{endpoint}"
     count = await redis.incr(key)
     if count == 1:
         await redis.expire(key, window_seconds)
     if count > max_requests:
         raise HTTPException(429, "请求过于频繁")
     ```
  2. 标识符使用 `client_ip + user_id` 组合
  3. 清理旧的内存实现

### 【F-05】Token 存储在 localStorage + 无自动刷新 + 无路由守卫
- **文件**: `frontend/src/stores/api.js`、`router/index.js`
- **修复要求**:
  1. **路由守卫**：在 `router/index.js` 添加全局 `beforeEach`：
     ```javascript
     router.beforeEach((to, from, next) => {
       const token = localStorage.getItem('token')
       if (to.meta.requiresAuth !== false && !token) {
         next({ path: '/login', query: { redirect: to.fullPath } })
       } else {
         next()
       }
     })
     ```
  2. **Axios Interceptor**：在 api.js 中添加响应拦截器：
     - 401 时清除 token 并跳转登录页
     - 403 时显示权限不足提示
  3. **Token 自动刷新**：利用 B-02 新增的 refresh_token 机制，在 access_token 过期前 5 分钟自动刷新

### 【F-06】扫描目标无前端格式校验
- **文件**: `frontend/src/views/Scanning.vue` 第 176-178 行
- **修复要求**:
  1. 添加前端目标格式校验函数：
     ```javascript
     function validateTarget(target) {
       // 支持: IP, 域名, URL, CIDR, IPv6
       const patterns = [
         /^(\d{1,3}\.){3}\d{1,3}(:\d+)?$/,
         /^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*(:\d+)?$/,
         /^https?:\/\/.+$/,
         /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/,
         /^\[[\da-fA-F:]+\](:\d+)?$/,
       ]
       return patterns.some(p => p.test(target.trim()))
     }
     ```
  2. 提交前逐行校验，无效目标标红并阻止提交
  3. 显示目标数量提示（如 `已输入 12/500 个目标`）

### 【F-07】所有列表页面使用内存全量分页，大数据集性能灾难
- **影响文件**: `Findings.vue`、`Assets.vue`、`Projects.vue`、`Knowledge.vue`、`Scanning.vue`
- **修复要求**:
  1. 改为**服务端分页**：
     ```javascript
     // 前端
     const res = await api.get('/projects/:id/findings', {
       params: { page: currentPage.value, page_size: pageSize.value, ...filters }
     })
     // 后端已有 Pagination 工具类，直接使用
     ```
  2. 前端只保留当前页数据，不再加载全量
  3. 分页组件改为服务端分页模式（total 由后端返回）
  4. 筛选/排序操作重新请求第一页

### 【F-08】SSH 凭据明文发送到后端
- **文件**: `frontend/src/views/Baseline.vue` 第 116-119 行
- **修复要求**:
  1. 发送前显示确认弹窗："即将将凭据发送到服务器进行基线扫描"
  2. 凭据字段使用 `type="password"` + `show-password` 切换
  3. 提交成功后清空凭据字段
  4. 后端接收后不要打印到日志

### 【F-09】用户管理页面可将自己降权导致无管理员
- **文件**: `frontend/src/views/Users.vue` 第 9-12 行 + 后端 `auth.py` 第 167-181 行
- **修复要求**:
  1. **前端**：角色变更前检查：
     - 是否修改的是当前登录用户自身
     - 是否为系统中最后一位活跃 admin
     - 任一条件为真时弹出二次确认警告
  2. **后端** `admin_update_user` 增加：
     ```python
     if user_id == current_user.id and req.get("role") != "admin":
         admin_count = db.execute(select(func.count(User.id)).where(...)).scalar()
         if admin_count <= 1:
             raise HTTPException(400, "不能降权最后一位管理员")
     ```

### 【F-10】AI 助手输入无长度限制和无速率限制
- **文件**: `frontend/src/views/AIAssistant.vue` 第 152-163 行
- **修复要求**:
  1. 前端限制单条消息最大长度（建议 4000 字符），超出截断并提示
  2. 添加发送冷却时间（如每条消息间隔最少 2 秒）
  3. 显示当前 token 用量估算（约 `len(msg) / 3` tokens）
  4. 敏感关键词检测：如果消息中疑似包含密钥/密码/Token 格式，弹出警告

### 【F-11】通知偏好切换后永不保存
- **文件**: `frontend/src/views/Notifications.vue` 第 69-75 行
- **修复要求**:
  1. 新增后端接口 `PUT /api/v1/user/preferences`
  2. `onMounted` 时从后端加载当前偏好设置
  3. 每次 switch 切变时调用保存接口（防抖 500ms）
  4. 后端存储在 User 表或独立的 UserPreferences 表

---

## 四、🟡 中危问题（应当修复，共 27 个）

### 【B-14】EngineOrchestrator _running_jobs 非线程安全
- **文件**: `backend/core/engine_orchestrator.py` 第 25, 86, 90 行
- **修复**: 使用 `asyncio.Lock()` 保护 `_running_jobs` 的读写操作，或改用 `dict` 的原子方法配合 copy-on-write

### 【B-15】PipelineExecutor 每次新建 EngineOrchestrator 实例，job tracking 不同步
- **文件**: `backend/core/pipeline_executor.py` 第 11 行
- **修复**: 改为接收外部注入的 orchestrator 单例，或使用模块级 `_global_orchestrator` 共享实例

### 【B-16】risk_scorer._is_private 对域名默认返回 True 导致评分偏低
- **文件**: `backend/core/risk_scorer.py` 第 49-55 行
- **修复**: 域名时应尝试 DNS 解析判断是否为内网地址，无法解析时返回 `False`（公网）而非 `True`

### 【B-17】截图上传文件名校验不充分，存在路径遍历风险
- **文件**: `backend/api/sessions.py` 第 122 行
- **修复**:
  1. 使用 `uuid.uuid4()` 重命名文件，不使用原始文件名
  2. 添加 magic bytes 校验（同 F-04）
  3. 文件大小硬限制（如 10MB）

### 【B-18】notify.py webhook 发送失败被静默忽略
- **文件**: `backend/core/notify.py` 全文
- **修复**:
  1. 添加重试机制（指数退避，最多 3 次）
  2. 失败时记录 error 级别日志
  3. 失败次数超过阈值时触发告警（邮件/钉钉等备用通道）
  4. 提供 webhook 健康状态查询接口

### 【B-19】admin_update_user 接受裸 dict，缺乏 Pydantic 校验
- **文件**: `backend/api/auth.py` 第 167-181 行
- **修复**:
  1. 定义 `AdminUpdateUserRequest(BaseModel)`：
     ```python
     class AdminUpdateUserRequest(BaseModel):
         display_name: Optional[str] = None
         email: Optional[EmailStr] = None
         role: Optional[Literal["admin", "engineer", "viewer"]] = None
         is_active: Optional[bool] = None
     ```
  2. role 字段使用 Literal enum 限制可选值

### 【B-20】get_system_settings 可能泄露敏感配置
- **文件**: `backend/api/auth.py` 第 184-200 行
- **修复**:
  1. LLM API Key 脱敏改为只显示后 4 位：`sk-****abcd`
  2. 不返回 `database_url`、`secret_key`、`redis_url` 等基础设施配置
  3. 前端 Settings 页面只显示可编辑字段

### 【B-21】扫描任务状态判断逻辑有缺陷
- **文件**: `backend/tasks/scan_worker.py` 第 119-122 行
- **修复**: 引入 `completed_with_errors` 状态——当部分 engine run failed 但有漏洞发现时使用此状态

### 【B-22】vuln_matcher 版本号比较元组对齐问题
- **文件**: `backend/core/vuln_matcher.py` 第 161-163, 125-148 行
- **修复**: 版本号比较时先对齐位数（补零到相同长度），再逐段比较。非数字部分（alpha/beta/rc）映射为数值权重。

### 【B-23】proxy_router 链构建方向需验证
- **文件**: `backend/core/proxy_router.py` 第 46-55 行
- **修复**: 写单元测试验证 proxychains 配置文件的链顺序是否符合 proxychains 的 ProxyList 规范（从最后一跳到第一跳）

### 【B-24】sanitizer SAFE_TARGET_PATTERN 过于严格
- **文件**: `backend/utils/sanitizer.py` 第 7 行
- **修复**: 放宽正则为 `^[a-zA-Z0-9.\-:\\/\[\]_%?#=@^~]+$`，但保留对 shell 元字符的过滤

### 【B-25】config.py @lru_cache 导致运行时无法热更新
- **文件**: `backend/config.py` 第 117-119 行
- **修复**: 移除 `@lru_cache`，改为带 TTL 的缓存（如 60 秒），或提供 `reload_settings()` 强制刷新方法

### 【B-26】dedup evidence 合并有类型混淆风险
- **文件**: `backend/core/dedup.py` 第 41-44 行
- **修复**: 合并前检查 evidence 类型，确保是 dict；嵌套合并时限制最大深度（如 3 层）

### 【B-27】scan_worker 每次循环新建 EngineOrchestrator
- **文件**: `backend/tasks/scan_worker.py` 第 77-79 行
- **修复**: 将 orchestrator 初始化移到 engines 循环外部，整个 task 共享一个实例

### 【F-13】Profile.vue 和 Settings.vue 个人设置功能完全重复
- **文件**: `frontend/src/views/Profile.vue` vs `Settings.vue`
- **修复**: 提取 `UserProfileForm` 公共组件，两个页面复用同一个组件

### 【F-14】ProjectDetail onMounted 串行发 6+ 请求 + 大量空 catch
- **文件**: `frontend/src/views/ProjectDetail.vue` onMounted
- **修复**:
  1. 改用 `Promise.allSettled` 并行请求
  2. catch 块中至少 `console.warn` 记录错误
  3. 首个请求失败时显示友好的"项目不存在"提示

### 【F-15】Scanning.vue 轮询定时器未在组件卸载时清理
- **文件**: `frontend/src/views/Scanning.vue`
- **修复**: 添加 `onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })`

### 【F-16】Assets.vue 快速扫描目标格式拼接不一致
- **文件**: `frontend/src/views/Assets.vue` 第 173-179 行
- **修复**: 统一使用 `host:port` 格式，IPv6 地址加方括号 `[::1]:8080`

### 【F-17】ManualTesting Checklist 进度除零 NaN
- **文件**: `frontend/src/views/ManualTesting.vue` 第 168 行
- **修复**: `checklistItems.length ? Math.round(checkedCount / checklistItems.length * 100) : 0`

### 【F-18】NetworkTopology ECharts 动态加载无兜底等待
- **文件**: `frontend/src/components/NetworkTopology.vue` 第 39-42, 88-129 行
- **修复**: 使用动态 import + loading 状态，ECharts 加载完成后再渲染

### 【F-19】Dashboard 全局统计无缓存
- **文件**: `frontend/src/views/Dashboard.vue`
- **修复**: 添加 stale-while-revalidate 策略，5 分钟内复用上次数据

### 【F-20】错误处理模式不统一（全项目）
- **影响**: 几乎所有 .vue 文件
- **修复**: 在 `stores/api.js` 中统一封装：
  ```javascript
  // 统一错误处理
  api.call = async (method, url, data) => {
    try {
      const res = await instance({ method, url, data })
      return res.data
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || '请求失败'
      ElMessage.error(msg)
      throw err  // 仍然抛出，让调用方可选处理
    }
  }
  ```

### 【F-21】路由参数 pid/id 从不校验有效性
- **影响**: Scanning, Findings, Assets, ProjectDetail, RedBlue, ManualTesting 等所有子页面
- **修复**: 在 router beforeEach 或各页面 onMounted 中校验 `route.params.id` 为有效数字，否则跳转到 404 或项目列表

### 【F-22】el-upload action URL 混用 /api/ 和 /api/v1/
- **影响**: ProjectDetail.vue 及其他含上传的页面
- **修复**: 统一使用 `/api/v1/` 前缀（与后端 main.py 路由注册一致），定义常量 `API_PREFIX = '/api/v1'`

### 【F-23】Findings 批量操作缺少二次确认
- **文件**: `frontend/src/views/Findings.vue` 第 6-7 行
- **修复**: 批量标记已修复/误报前加 `ElMessageBox.confirm('确认批量操作 N 条记录？')`

### 【F-24】ScopeManager 边界规则目标值无格式校验
- **文件**: `frontend/src/components/ScopeManager.vue` 第 48 行
- **修复**: 根据 target_type 做对应格式校验：
  - domain: 允许 `*.` 通配
  - ip: IPv4/IPv6 格式
  - cidr: `IP/掩码` 格式
  - url: 必须以 `http://` 或 `https://` 开头
  - port: 1-65535 数字

---

## 五、🔗 跨层关联问题（5 个，需前后端协同修复）

| ID | 关联问题 | 修复要点 |
|----|---------|---------|
| **X-1** | F-2 客户端权限判断 + B-20 后端敏感配置返回 | 前端改用接口获取角色 + 后端脱敏不返回基础设施配置 |
| **X-2** | F-9 自我降权 + B-19 后端不阻止 | 前后端都加"最后管理员"保护 |
| **X-3** | F-4 img 直接渲染 + B-17 上传只校验扩展名 | 前端协议白名单 + 后端 magic bytes 校验 |
| **X-4** | F-22 API 前缀混用 + 后端两套路由 | 统一为 `/api/v1/`，清理冗余路由注册 |
| **X-5** | F-11 偏好不持久 + B-18 webhook 静默失败 | 新增偏好 CRUD 接口 + webhook 重试+告警 |

---

## 六、通用修复要求（适用于所有改动）

### 代码质量
1. **DRY 原则**：提取公共逻辑为工具函数/组件，消除重复代码
2. **类型注解**：所有新增/修改的 Python 函数必须有完整的 type hints
3. **错误处理**：不允许空的 `except: pass`，至少 `logging.warning`
4. **日志规范**：使用 structured logging，包含 `user_id`、`project_id`、`action` 字段

### 安全加固
1. 所有用户输入必须经过 sanitize（即使前端已校验）
2. 所有 SQL 查询使用 ORM/参数化查询，禁止 f-string 拼接 SQL
3. 敏感数据（密码、Token、Key）不得出现在日志中
4. API 响应不返回内部实现细节（堆栈信息、内部路径等）

### 测试要求
1. 每个 Bug 修复必须配套至少一个单元测试
2. B-07（Pipeline targets 覆盖）需要多依赖 DAG 的集成测试
3. B-06（SSRF）需要 DNS Rebinding 场景的安全测试
4. F-01（TerminalPanel WS）需要 WebSocket 连接测试

### 向后兼容
1. API 变更保持向后兼容（旧字段 deprecated 但仍返回）
2. 数据库 migration 使用 Alembic，不可破坏现有数据
3. 前端路由变更添加 redirect 规则

---

## 七、修复优先级排序（推荐执行顺序）

```
第一批（阻断性 Bug，影响核心功能可用性）:
  F-01  TerminalPanel WS URL 断裂        → 改 1 行
  F-03  NetworkTopology 模板变量丢失      → 补全变量
  B-07  Pipeline targets 覆盖 bug        → 改 5 行

第二批（安全漏洞，可被利用）:
  B-01  注册无限流                       → 加限流中间件
  B-04  终端 fork bash                   → 加 rbash + 审计
  F-02  客户端权限伪造                   → 改 store 取角色
  B-05  命令注入风险                     → 加强 sanitize
  B-06  SSRF DNS Rebinding              → 二次验证 IP

第三批（架构缺陷，影响稳定性）:
  B-09  连接池过载                       → 调低参数
  B-08  事务不一致                       → 改 async
  B-13  限流失效                         → 迁移 Redis
  B-02  JWT 过时                        → 加 refresh token
  F-05  无路由守卫 + Token 管理          → 加 interceptor

第四批（体验/健壮性问题，共 37 个）:
  其余 🟠 高危 + 🟡 中危问题，按编号顺序逐一修复
```

---

## 八、验收标准

修复完成后，需满足以下全部条件：

- [ ] 所有 🔴 严重问题（10个）已修复且有测试覆盖
- [ ] 所有 🟠 高危问题（15个）已修复
- [ ] 所有 🟡 中危问题（27个）已修复或有明确的"暂不修复"理由
- [ ] 项目可以正常启动（`docker-compose up` 或 `make dev`）
- [ ] 注册/登录/登出流程正常
- [ ] 创建项目 → 添加资产 → 执行扫描 → 查看漏洞 主流程跑通
- [ ] 终端面板 WebSocket 可以正常连接和交互
- [ ] 网络拓扑图节点名称正确显示
- [ ] 前端所有页面无控制台报错
- [ ] `pytest backend/tests/` 全部通过（如有测试）
- [ ] 无新的 lint error / type check warning

---

*文档版本: v1.0 | 审查日期: 2026-06-25 | 覆盖文件数: 53 | 发现问题数: 52*
