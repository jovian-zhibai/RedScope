<template>
  <div>
    <h2 style="margin-bottom: 16px;">通知设置</h2>

    <!-- Webhook Config -->
    <div class="card" style="padding: 20px; margin-bottom: 16px;">
      <h3 style="margin-bottom: 16px;">Webhook 通知</h3>
      <el-form :model="webhookForm" label-width="100px">
        <el-form-item label="通知渠道">
          <el-select v-model="webhookForm.channel">
            <el-option value="wecom" label="企业微信" /><el-option value="dingtalk" label="钉钉" />
            <el-option value="feishu" label="飞书" /><el-option value="slack" label="Slack" />
            <el-option value="telegram" label="Telegram" /><el-option value="custom" label="自定义 Webhook" />
          </el-select>
        </el-form-item>
        <el-form-item label="Webhook URL"><el-input v-model="webhookForm.webhook_url" placeholder="https://..." /></el-form-item>
        <el-form-item label="测试消息"><el-input v-model="webhookForm.message" /></el-form-item>
        <el-form-item>
          <el-button type="primary" @click="testWebhook" :loading="testing">发送测试通知</el-button>
        </el-form-item>
      </el-form>
      <div v-if="testResult" style="margin-top: 8px;">
        <el-tag :type="testResult.status === 'sent' ? 'success' : 'danger'">
          {{ testResult.status === 'sent' ? '发送成功' : `发送失败: ${testResult.error}` }}
        </el-tag>
      </div>
    </div>

    <!-- Notification Preferences -->
    <div class="card" style="padding: 20px; margin-bottom: 16px;">
      <h3 style="margin-bottom: 16px;">通知偏好</h3>
      <div style="display: grid; gap: 12px;">
        <div v-for="pref in preferences" :key="pref.key" style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--rs-border);">
          <div>
            <div>{{ pref.label }}</div>
            <div style="font-size: 12px; color: var(--rs-text-secondary);">{{ pref.desc }}</div>
          </div>
          <el-switch v-model="pref.enabled" size="small" />
        </div>
      </div>
    </div>

    <!-- In-App Notifications -->
    <div class="card" style="padding: 20px;">
      <h3 style="margin-bottom: 16px;">最近通知</h3>
      <div v-for="n in notifications" :key="n.id" style="padding: 10px 0; border-bottom: 1px solid var(--rs-border);">
        <div style="display: flex; justify-content: space-between;">
          <div>
            <el-tag :type="n.level === 'error' ? 'danger' : n.level === 'warning' ? 'warning' : 'info'" size="small" style="margin-right: 8px;">{{ n.level }}</el-tag>
            <span>{{ n.message }}</span>
          </div>
          <span style="font-size: 12px; color: var(--rs-text-secondary);">{{ n.time }}</span>
        </div>
      </div>
      <el-empty v-if="!notifications.length" description="暂无通知" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const webhookForm = ref({ channel: 'wecom', webhook_url: '', message: 'RedScope 通知测试' })
const testing = ref(false)
const testResult = ref(null)

const preferences = ref([
  { key: 'scan_complete', label: '扫描完成通知', desc: '扫描任务完成时推送', enabled: true },
  { key: 'critical_vuln', label: '严重漏洞告警', desc: '发现严重/高危漏洞时推送', enabled: true },
  { key: 'auth_expiry', label: '授权到期提醒', desc: '项目授权即将到期时提醒', enabled: true },
  { key: 'retest_request', label: '复测申请通知', desc: '客户提交复测申请时通知', enabled: false },
  { key: 'order_status', label: '工单状态变更', desc: '工单审批/完成时通知', enabled: false },
])

const notifications = ref([])

const testWebhook = async () => {
  if (!webhookForm.value.webhook_url) { ElMessage.warning('请输入 Webhook URL'); return }
  testing.value = true
  testResult.value = null
  try {
    const res = await api.post('/notify/test', webhookForm.value)
    testResult.value = res
  } catch (e) { testResult.value = { status: 'failed', error: '请求失败' } }
  finally { testing.value = false }
}
</script>
