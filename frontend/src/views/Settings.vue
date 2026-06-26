<template>
  <div style="max-width: 900px;">
    <h2 style="margin-bottom: 20px;">系统管理</h2>
    <el-tabs v-model="activeTab">
      <!-- 系统配置 (admin only) -->
      <el-tab-pane label="系统配置" name="system">
        <div v-if="!isAdmin" style="padding: 40px; text-align: center; color: var(--rs-text-secondary);">仅管理员可查看系统配置</div>
        <div v-else>
          <div class="card" style="margin-top: 12px;">
            <h3 style="margin-bottom: 16px;">AI / LLM 配置</h3>
            <el-form :model="sysConfig" label-width="140px">
              <el-form-item label="API Key"><el-input v-model="sysConfig.llm_api_key" placeholder="sk-..." type="password" show-password /></el-form-item>
              <el-form-item label="API 地址"><el-input v-model="sysConfig.llm_base_url" placeholder="https://api.deepseek.com" /></el-form-item>
              <el-form-item label="模型名称"><el-input v-model="sysConfig.llm_model" placeholder="deepseek-chat" /></el-form-item>
              <el-form-item label="NVD API Key"><el-input v-model="sysConfig.nvd_api_key" placeholder="NVD 漏洞情报抓取用" type="password" show-password /></el-form-item>
              <el-form-item>
                <el-button @click="testLLM" :loading="testingLLM">测试连通性</el-button>
                <el-tag v-if="llmTestResult" :type="llmTestResult.status === 'ok' ? 'success' : 'danger'" style="margin-left: 12px;">
                  {{ llmTestResult.status === 'ok' ? '连接成功' : '失败: ' + llmTestResult.error }}
                </el-tag>
              </el-form-item>
            </el-form>
          </div>

          <div class="card">
            <h3 style="margin-bottom: 16px;">通知配置</h3>
            <el-form :model="sysConfig" label-width="140px">
              <el-form-item label="Webhook URL"><el-input v-model="sysConfig.notify_webhook_url" /></el-form-item>
              <el-form-item label="通知渠道">
                <el-select v-model="sysConfig.notify_channel" style="width: 100%;">
                  <el-option value="wecom" label="企业微信" /><el-option value="dingtalk" label="钉钉" />
                  <el-option value="feishu" label="飞书" /><el-option value="slack" label="Slack" />
                  <el-option value="telegram" label="Telegram" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>

          <div class="card">
            <h3 style="margin-bottom: 16px;">扫描配置</h3>
            <el-form :model="sysConfig" label-width="140px">
              <el-form-item label="最大并发扫描"><el-input-number v-model="sysConfig.max_concurrent_scans" :min="1" :max="50" /></el-form-item>
              <el-form-item label="单次最大目标数"><el-input-number v-model="sysConfig.max_targets_per_scan" :min="1" :max="10000" /></el-form-item>
            </el-form>
          </div>

          <div class="card">
            <h3 style="margin-bottom: 16px;">运行环境</h3>
            <el-form label-width="140px">
              <el-form-item label="环境"><el-tag>{{ sysConfig.environment }}</el-tag></el-form-item>
            </el-form>
            <div style="font-size: 12px; color: var(--rs-text-secondary);">安全类配置（SECRET_KEY、数据库密码、Redis密码）只能在 .env 文件中修改</div>
          </div>

          <div style="margin-top: 16px;">
            <el-button type="primary" size="large" @click="saveSystemConfig" :loading="savingSys">保存所有配置</el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- 用户管理 -->
      <el-tab-pane label="用户管理" name="users" v-if="isAdmin">
        <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
          <el-button type="primary" size="small" @click="showCreateUser = true">创建用户</el-button>
        </div>
        <div>
          <el-table :data="users" style="width: 100%;">
            <el-table-column prop="username" label="用户名" width="120" />
            <el-table-column prop="display_name" label="显示名" width="150" />
            <el-table-column prop="role" label="角色" width="120">
              <template #default="{ row }">
                <el-select :model-value="row.role" size="small" @change="updateUser(row.id, { role: $event })">
                  <el-option value="admin" label="管理员" /><el-option value="leader" label="组长" />
                  <el-option value="engineer" label="工程师" /><el-option value="viewer" label="观察者" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="email" label="邮箱" min-width="180" />
            <el-table-column prop="is_active" label="状态" width="80">
              <template #default="{ row }">
                <el-switch :model-value="row.is_active" @change="updateUser(row.id, { is_active: $event })" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="last_login_at" label="最后登录" width="120">
              <template #default="{ row }">{{ row.last_login_at?.split('T')[0] || '从未' }}</template>
            </el-table-column>
          </el-table>
        </div>

        <el-dialog v-model="showCreateUser" title="创建用户" width="460px">
          <el-form :model="newUserForm" label-width="80px">
            <el-form-item label="用户名"><el-input v-model="newUserForm.username" placeholder="至少3位" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="newUserForm.password" placeholder="至少8位，含字母+数字" type="password" show-password /></el-form-item>
            <el-form-item label="显示名"><el-input v-model="newUserForm.display_name" /></el-form-item>
            <el-form-item label="角色">
              <el-select v-model="newUserForm.role">
                <el-option value="admin" label="管理员" /><el-option value="manager" label="经理" />
                <el-option value="leader" label="组长" /><el-option value="engineer" label="工程师" />
                <el-option value="viewer" label="观察者" />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showCreateUser = false">取消</el-button>
            <el-button type="primary" @click="createUser" :loading="creatingUser">创建</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- 租户管理 -->
      <el-tab-pane label="租户管理" name="tenants" v-if="isAdmin">
        <div style="margin-top: 12px;">
          <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
            <el-button type="primary" size="small" @click="showCreateTenant = true">新建租户</el-button>
          </div>
          <el-table :data="tenants" style="width: 100%;" @row-click="selectTenant">
            <el-table-column prop="name" label="租户名称" min-width="200" />
            <el-table-column prop="slug" label="标识" width="120" />
            <el-table-column prop="user_count" label="用户数" width="100" />
            <el-table-column prop="max_users" label="上限" width="80" />
            <el-table-column prop="is_active" label="状态" width="80"><template #default="{ row }">{{ row.is_active ? '启用' : '禁用' }}</template></el-table-column>
          </el-table>
        </div>

        <el-dialog v-model="showCreateTenant" title="新建租户" width="480px">
          <el-form :model="tenantForm" label-width="80px">
            <el-form-item label="名称"><el-input v-model="tenantForm.name" /></el-form-item>
            <el-form-item label="标识"><el-input v-model="tenantForm.slug" placeholder="英文标识" /></el-form-item>
            <el-form-item label="用户上限"><el-input-number v-model="tenantForm.max_users" :min="1" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showCreateTenant = false">取消</el-button>
            <el-button type="primary" @click="createTenant">创建</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- 系统日志 -->
      <el-tab-pane label="审计日志" name="logs" v-if="isAdmin">
        <div style="margin-top: 12px;">
          <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
            <el-button size="small" @click="loadLogs">刷新</el-button>
          </div>
          <el-table :data="auditLogs" style="width: 100%;" size="small">
            <el-table-column prop="action" label="操作" min-width="200" />
            <el-table-column prop="severity" label="级别" width="80">
              <template #default="{ row }">
                <el-tag :type="{critical:'danger',high:'warning',info:'info'}[row.severity]" size="small">{{ row.severity }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="user_id" label="用户ID" width="80" />
            <el-table-column prop="ip_address" label="IP" width="130" />
            <el-table-column prop="detail" label="详情" min-width="150">
              <template #default="{ row }"><span style="font-size: 12px;">{{ row.detail }}</span></template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="160">
              <template #default="{ row }">{{ row.created_at?.replace('T', ' ').slice(0, 19) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!auditLogs.length" description="暂无日志" />
        </div>
      </el-tab-pane>

      <!-- 通知设置 -->
      <el-tab-pane label="通知测试" name="notifications">
        <div class="card" style="margin-top: 12px;">
          <h3 style="margin-bottom: 16px;">Webhook 通知测试</h3>
          <el-form :model="webhookForm" label-width="100px">
            <el-form-item label="通知渠道">
              <el-select v-model="webhookForm.channel">
                <el-option value="wecom" label="企业微信" /><el-option value="dingtalk" label="钉钉" />
                <el-option value="feishu" label="飞书" /><el-option value="slack" label="Slack" />
                <el-option value="telegram" label="Telegram" />
              </el-select>
            </el-form-item>
            <el-form-item label="Webhook URL"><el-input v-model="webhookForm.webhook_url" placeholder="https://..." /></el-form-item>
            <el-form-item label="测试消息"><el-input v-model="webhookForm.message" /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="testWebhook" :loading="testing">发送测试</el-button>
              <el-tag v-if="testResult" :type="testResult.status === 'sent' ? 'success' : 'danger'" style="margin-left: 12px;">
                {{ testResult.status === 'sent' ? '发送成功' : '发送失败' }}
              </el-tag>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const activeTab = ref('system')

const isAdmin = computed(() => {
  try {
    const token = localStorage.getItem('token')
    if (!token) return false
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.role === 'admin'
  } catch { return false }
})

// System config
const sysConfig = ref({})
const savingSys = ref(false)
const testingLLM = ref(false)
const llmTestResult = ref(null)

const saveSystemConfig = async () => {
  savingSys.value = true
  try {
    await api.put('/auth/settings/system', {
      llm_api_key: sysConfig.value.llm_api_key,
      llm_base_url: sysConfig.value.llm_base_url,
      llm_model: sysConfig.value.llm_model,
      nvd_api_key: sysConfig.value.nvd_api_key,
      notify_webhook_url: sysConfig.value.notify_webhook_url,
      notify_channel: sysConfig.value.notify_channel,
      max_concurrent_scans: String(sysConfig.value.max_concurrent_scans),
      max_targets_per_scan: String(sysConfig.value.max_targets_per_scan),
    })
    ElMessage.success('配置已保存')
  } catch (e) { ElMessage.error('保存失败') }
  finally { savingSys.value = false }
}

const testLLM = async () => {
  testingLLM.value = true
  llmTestResult.value = null
  try {
    if (sysConfig.value.llm_api_key && !sysConfig.value.llm_api_key.startsWith('****')) {
      await saveSystemConfig()
    }
    llmTestResult.value = await api.post('/auth/settings/test-llm')
  } catch (e) { llmTestResult.value = { status: 'failed', error: '请求失败' } }
  finally { testingLLM.value = false }
}

// Users
const users = ref([])
const loadUsers = async () => {
  try { const res = await api.get('/auth/users'); users.value = res.items || [] } catch {}
}
const updateUser = async (id, data) => {
  try { await api.put(`/auth/users/${id}`, data); ElMessage.success('已更新'); await loadUsers() }
  catch (e) { ElMessage.error(e.response?.data?.detail || '更新失败') }
}

const showCreateUser = ref(false)
const creatingUser = ref(false)
const newUserForm = ref({ username: '', password: '', display_name: '', role: 'engineer' })
const createUser = async () => {
  if (!newUserForm.value.username || !newUserForm.value.password) { ElMessage.warning('请填写用户名和密码'); return }
  creatingUser.value = true
  try {
    await api.post('/auth/users', newUserForm.value)
    ElMessage.success('用户已创建')
    showCreateUser.value = false
    newUserForm.value = { username: '', password: '', display_name: '', role: 'engineer' }
    await loadUsers()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '创建失败') }
  finally { creatingUser.value = false }
}

// Tenants
const tenants = ref([])
const showCreateTenant = ref(false)
const tenantForm = ref({ name: '', slug: '', max_users: 50 })
const loadTenants = async () => {
  try { const res = await api.get('/tenants'); tenants.value = res.items || [] } catch {}
}
const createTenant = async () => {
  try {
    await api.post('/tenants', tenantForm.value)
    showCreateTenant.value = false
    ElMessage.success('租户已创建')
    await loadTenants()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '创建失败') }
}
const selectTenant = (row) => { /* future: show tenant detail drawer */ }

// Logs
const auditLogs = ref([])
const loadLogs = async () => {
  try { const res = await api.get('/auth/audit-logs'); auditLogs.value = res.items || [] } catch {}
}

// Notifications
const webhookForm = ref({ channel: 'wecom', webhook_url: '', message: 'RedScope 通知测试' })
const testing = ref(false)
const testResult = ref(null)

const testWebhook = async () => {
  if (!webhookForm.value.webhook_url) { ElMessage.warning('请输入 Webhook URL'); return }
  testing.value = true
  testResult.value = null
  try {
    const res = await api.post('/notify/test', webhookForm.value)
    testResult.value = res
  } catch (e) { testResult.value = { status: 'failed' } }
  finally { testing.value = false }
}

onMounted(async () => {
  if (isAdmin.value) {
    try { sysConfig.value = await api.get('/auth/settings/system') } catch {}
    await Promise.all([loadUsers(), loadTenants(), loadLogs()])
  }
})
</script>
