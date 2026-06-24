<template>
  <div style="min-height: 100vh; background: var(--rs-bg-primary);">
    <!-- Login -->
    <div v-if="!loggedIn" style="display: flex; justify-content: center; align-items: center; height: 100vh;">
      <div class="card" style="width: 400px;">
        <h2 style="text-align: center; color: var(--rs-accent); margin-bottom: 24px;">🔒 客户门户</h2>
        <el-form :model="loginForm" @submit.prevent="doLogin">
          <el-form-item><el-input v-model="loginForm.username" placeholder="客户账号" size="large" /></el-form-item>
          <el-form-item><el-input v-model="loginForm.password" placeholder="密码" type="password" size="large" show-password /></el-form-item>
          <el-button type="primary" style="width: 100%;" size="large" @click="doLogin" :loading="logging">登录</el-button>
        </el-form>
      </div>
    </div>

    <!-- Portal Content -->
    <div v-else style="max-width: 1000px; margin: 0 auto; padding: 24px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
        <div>
          <h2 style="color: var(--rs-text-primary);">{{ overview.project_name }}</h2>
          <span style="color: var(--rs-text-secondary);">客户: {{ overview.client_name }}</span>
        </div>
        <el-button size="small" @click="logout">退出</el-button>
      </div>

      <!-- Stats -->
      <div class="stat-grid" style="margin-bottom: 24px;">
        <div class="stat-card critical"><div class="stat-label">漏洞总数</div><div class="stat-value">{{ overview.total_findings }}</div></div>
        <div class="stat-card" style="border-left: 3px solid var(--rs-danger);"><div class="stat-label">严重/高危</div><div class="stat-value">{{ (overview.severities?.critical || 0) + (overview.severities?.high || 0) }}</div></div>
        <div class="stat-card success"><div class="stat-label">已修复</div><div class="stat-value">{{ overview.fixed }}</div></div>
        <div class="stat-card info"><div class="stat-label">修复率</div><div class="stat-value">{{ overview.fix_rate }}%</div></div>
      </div>

      <!-- Severity Breakdown -->
      <div class="card" style="padding: 16px; margin-bottom: 24px;">
        <h3 style="margin-bottom: 12px; color: var(--rs-text-primary);">漏洞等级分布</h3>
        <div style="display: flex; gap: 16px;">
          <div v-for="(count, sev) in overview.severities" :key="sev" style="flex: 1; text-align: center;">
            <div style="font-size: 28px; font-weight: bold;" :style="{ color: sevColor(sev) }">{{ count }}</div>
            <div style="font-size: 12px; color: var(--rs-text-secondary);">{{ sevLabel(sev) }}</div>
            <div style="margin-top: 4px; height: 4px; border-radius: 2px;" :style="{ background: sevColor(sev), width: barWidth(count) + '%' }" />
          </div>
        </div>
      </div>

      <!-- Findings Table -->
      <div class="card" style="padding: 16px; margin-bottom: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <h3 style="color: var(--rs-text-primary);">漏洞列表</h3>
          <el-button size="small" @click="requestRetest" :disabled="!selectedIds.length">
            申请复测 ({{ selectedIds.length }})
          </el-button>
        </div>
        <el-table :data="findings" style="width: 100%;" @selection-change="onSelect">
          <el-table-column type="selection" width="40" />
          <el-table-column prop="title" label="漏洞名称" min-width="250" />
          <el-table-column prop="severity" label="等级" width="80">
            <template #default="{ row }"><span class="severity-badge" :class="row.severity">{{ row.severity }}</span></template>
          </el-table-column>
          <el-table-column prop="vuln_type" label="类型" width="120" />
          <el-table-column prop="description" label="描述" min-width="200">
            <template #default="{ row }">
              <span style="font-size: 12px; color: var(--rs-text-secondary);">{{ row.description?.slice(0, 100) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="solution" label="修复建议" min-width="200">
            <template #default="{ row }">
              <span style="font-size: 12px;">{{ row.solution }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="fix_status" label="修复状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.fix_status === 'fixed' ? 'success' : row.fix_status === 'fixing' ? 'warning' : 'danger'" size="small">
                {{ {unfixed:'未修复', fixing:'修复中', fixed:'已修复'}[row.fix_status] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button v-if="row.fix_status === 'unfixed'" size="small" @click="markFixed(row.id)">标记已修</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Reports -->
      <div class="card" style="padding: 16px;">
        <h3 style="margin-bottom: 12px; color: var(--rs-text-primary);">渗透测试报告</h3>
        <el-table :data="reports" style="width: 100%;">
          <el-table-column prop="title" label="报告名称" min-width="250" />
          <el-table-column prop="report_type" label="类型" width="100" />
          <el-table-column prop="format" label="格式" width="80" />
          <el-table-column prop="generated_at" label="生成时间" width="180" />
        </el-table>
        <el-empty v-if="!reports.length" description="暂无报告" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const loggedIn = ref(false)
const logging = ref(false)
const loginForm = ref({ username: '', password: '' })

let clientToken = ''
let projectId = null

const overview = ref({})
const findings = ref([])
const reports = ref([])
const selectedIds = ref([])

const portalApi = axios.create({ baseURL: '/api/portal', timeout: 30000 })

const doLogin = async () => {
  logging.value = true
  try {
    const res = await portalApi.post('/login', loginForm.value)
    clientToken = res.data.access_token
    projectId = res.data.project_id
    portalApi.defaults.headers.common['Authorization'] = `Bearer ${clientToken}`
    loggedIn.value = true
    await loadPortalData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally { logging.value = false }
}

const logout = () => { loggedIn.value = false; clientToken = ''; projectId = null }

const loadPortalData = async () => {
  const [ov, fd, rp] = await Promise.all([
    portalApi.get(`/project/${projectId}/overview`),
    portalApi.get(`/project/${projectId}/findings`),
    portalApi.get(`/project/${projectId}/reports`),
  ])
  overview.value = ov.data
  findings.value = fd.data.items || []
  reports.value = rp.data.items || []
}

const onSelect = (rows) => { selectedIds.value = rows.map(r => r.id) }

const markFixed = async (findingId) => {
  await portalApi.put(`/project/${projectId}/findings/${findingId}/mark-fixed`)
  ElMessage.success('已标记为修复中')
  await loadPortalData()
}

const requestRetest = async () => {
  await portalApi.post(`/project/${projectId}/request-retest`, { finding_ids: selectedIds.value })
  ElMessage.success(`已提交 ${selectedIds.value.length} 个漏洞的复测申请`)
  await loadPortalData()
}

const sevColor = (sev) => ({ critical: '#e74c3c', high: '#e67e22', medium: '#f1c40f', low: '#3498db', info: '#95a5a6' }[sev] || '#95a5a6')
const sevLabel = (sev) => ({ critical: '严重', high: '高危', medium: '中危', low: '低危', info: '信息' }[sev] || sev)
const barWidth = (count) => {
  const max = Math.max(...Object.values(overview.value.severities || {}), 1)
  return Math.round(count / max * 100)
}
</script>
