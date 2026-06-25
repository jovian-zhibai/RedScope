<template>
  <div style="max-width: 800px;">
    <h2 style="margin-bottom: 20px;">设置</h2>
    <el-tabs v-model="activeTab">
      <!-- 个人设置 -->
      <el-tab-pane label="个人信息" name="profile">
        <div class="card" style="margin-top: 12px;">
          <el-form :model="profile" label-width="80px">
            <el-form-item label="用户名"><el-input :model-value="profile.username" disabled /></el-form-item>
            <el-form-item label="角色"><el-tag>{{ profile.role }}</el-tag></el-form-item>
            <el-form-item label="显示名"><el-input v-model="profile.display_name" /></el-form-item>
            <el-form-item label="邮箱"><el-input v-model="profile.email" /></el-form-item>
            <el-form-item label="手机"><el-input v-model="profile.phone" /></el-form-item>
            <el-form-item><el-button type="primary" @click="saveProfile" :loading="saving">保存</el-button></el-form-item>
          </el-form>
        </div>
        <div class="card">
          <h3 style="margin-bottom: 16px;">修改密码</h3>
          <el-form :model="pwdForm" label-width="80px">
            <el-form-item label="原密码"><el-input v-model="pwdForm.old_password" type="password" show-password /></el-form-item>
            <el-form-item label="新密码"><el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少8位，含字母+数字" /></el-form-item>
            <el-form-item label="确认"><el-input v-model="pwdForm.confirm" type="password" show-password /></el-form-item>
            <el-form-item><el-button type="warning" @click="changePassword" :loading="changingPwd">修改密码</el-button></el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- 通知设置 -->
      <el-tab-pane label="通知设置" name="notifications">
        <div class="card" style="margin-top: 12px;">
          <h3 style="margin-bottom: 16px;">Webhook 通知</h3>
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
        <div class="card">
          <h3 style="margin-bottom: 16px;">通知偏好</h3>
          <div v-for="pref in preferences" :key="pref.key" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--rs-border);">
            <div>
              <div>{{ pref.label }}</div>
              <div style="font-size: 12px; color: var(--rs-text-secondary);">{{ pref.desc }}</div>
            </div>
            <el-switch v-model="pref.enabled" size="small" />
          </div>
        </div>
      </el-tab-pane>

      <!-- 系统配置 (admin only) -->
      <el-tab-pane v-if="isAdmin" label="系统配置" name="system">
        <div class="card" style="margin-top: 12px;">
          <h3 style="margin-bottom: 16px;">AI / LLM 配置</h3>
          <el-form :model="sysConfig" label-width="140px">
            <el-form-item label="API Key"><el-input v-model="sysConfig.llm_api_key" placeholder="sk-..." type="password" show-password /></el-form-item>
            <el-form-item label="API 地址">
              <el-input v-model="sysConfig.llm_base_url" placeholder="https://api.deepseek.com/v1/chat/completions" />
              <div style="font-size: 11px; color: var(--rs-text-secondary); margin-top: 4px;">填完整地址（含 /v1/chat/completions）或只填域名均可</div>
            </el-form-item>
            <el-form-item label="模型名称"><el-input v-model="sysConfig.llm_model" placeholder="deepseek-chat" /></el-form-item>
            <el-form-item label="NVD API Key">
              <el-input v-model="sysConfig.nvd_api_key" placeholder="NVD 漏洞情报抓取用，从 nvd.nist.gov 申请" type="password" show-password />
            </el-form-item>
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
            <el-form-item label="Webhook URL"><el-input v-model="sysConfig.notify_webhook_url" placeholder="https://qyapi.weixin.qq.com/..." /></el-form-item>
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
          <h3 style="margin-bottom: 16px;">网络配置</h3>
          <el-form :model="sysConfig" label-width="140px">
            <el-form-item label="CORS Origins">
              <el-input v-model="sysConfig.cors_origins" placeholder="http://localhost:3000,http://127.0.0.1:3000" />
              <div style="font-size: 11px; color: var(--rs-text-secondary); margin-top: 4px;">多个地址用逗号分隔，修改后需重启生效</div>
            </el-form-item>
            <el-form-item label="运行环境"><el-tag>{{ sysConfig.environment }}</el-tag></el-form-item>
          </el-form>
        </div>

        <div style="margin-top: 16px; display: flex; gap: 8px;">
          <el-button type="primary" size="large" @click="saveSystemConfig" :loading="savingSys">保存所有配置</el-button>
          <div style="font-size: 12px; color: var(--rs-text-secondary); line-height: 40px;">
            安全类配置（SECRET_KEY、数据库密码、Redis密码）只能在 .env 文件中修改
          </div>
        </div>
      </el-tab-pane>

      <!-- 系统日志 (admin only) -->
      <el-tab-pane v-if="isAdmin" label="系统日志" name="logs">
        <div class="card" style="margin-top: 12px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
            <h3>操作审计日志</h3>
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
              <template #default="{ row }"><span style="font-size: 12px; color: var(--rs-text-secondary);">{{ row.detail }}</span></template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="160">
              <template #default="{ row }">{{ row.created_at?.replace('T', ' ').slice(0, 19) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!auditLogs.length" description="暂无日志" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const activeTab = ref('profile')

const isAdmin = computed(() => {
  try {
    const token = localStorage.getItem('token')
    if (!token) return false
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.role === 'admin'
  } catch { return false }
})

// Profile
const profile = ref({ username: '', display_name: '', email: '', phone: '', role: '' })
const pwdForm = ref({ old_password: '', new_password: '', confirm: '' })
const saving = ref(false)
const changingPwd = ref(false)

const saveProfile = async () => {
  saving.value = true
  try {
    await api.put('/auth/me', { display_name: profile.value.display_name, email: profile.value.email, phone: profile.value.phone })
    ElMessage.success('保存成功')
  } catch (e) { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

const changePassword = async () => {
  if (pwdForm.value.new_password !== pwdForm.value.confirm) { ElMessage.warning('两次密码不一致'); return }
  changingPwd.value = true
  try {
    await api.post('/auth/change-password', { old_password: pwdForm.value.old_password, new_password: pwdForm.value.new_password })
    ElMessage.success('密码修改成功')
    pwdForm.value = { old_password: '', new_password: '', confirm: '' }
  } catch (e) { ElMessage.error(e.response?.data?.detail || '修改失败') }
  finally { changingPwd.value = false }
}

// Notifications
const webhookForm = ref({ channel: 'wecom', webhook_url: '', message: 'RedScope 通知测试' })
const testing = ref(false)
const testResult = ref(null)
const preferences = ref([
  { key: 'scan_complete', label: '扫描完成通知', desc: '扫描任务完成时推送', enabled: true },
  { key: 'critical_vuln', label: '严重漏洞告警', desc: '发现严重/高危漏洞时即时推送', enabled: true },
  { key: 'auth_expiry', label: '授权到期提醒', desc: '项目授权即将到期时提醒', enabled: true },
  { key: 'retest_request', label: '复测申请通知', desc: '客户提交复测申请时通知', enabled: false },
])

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

// System config (admin only)
const sysConfig = ref({})
const auditLogs = ref([])
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
      cors_origins: sysConfig.value.cors_origins,
    })
    ElMessage.success('所有配置已保存')
  } catch (e) { ElMessage.error('保存失败') }
  finally { savingSys.value = false }
}

const testLLM = async () => {
  testingLLM.value = true
  llmTestResult.value = null
  try {
    if (sysConfig.value.llm_api_key && !sysConfig.value.llm_api_key.startsWith('***')) {
      await saveSystemConfig()
    }
    llmTestResult.value = await api.post('/auth/settings/test-llm')
  } catch (e) { llmTestResult.value = { status: 'failed', error: '请求失败' } }
  finally { testingLLM.value = false }
}

const loadLogs = async () => {
  try { const res = await api.get('/auth/audit-logs'); auditLogs.value = res.items || [] }
  catch { auditLogs.value = [] }
}

onMounted(async () => {
  try { profile.value = await api.get('/auth/me') } catch {}
  if (isAdmin.value) {
    try { sysConfig.value = await api.get('/auth/settings/system') } catch {}
    await loadLogs()
  }
})
</script>
