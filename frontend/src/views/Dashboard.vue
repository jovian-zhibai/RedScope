<template>
  <div>
    <div class="stat-grid">
      <div class="stat-card info">
        <div class="stat-label">进行中项目</div>
        <div class="stat-value">{{ stats.activeProjects }}</div>
      </div>
      <div class="stat-card warning">
        <div class="stat-label">发现漏洞</div>
        <div class="stat-value">{{ stats.totalFindings }}</div>
      </div>
      <div class="stat-card critical">
        <div class="stat-label">严重/高危</div>
        <div class="stat-value">{{ stats.criticalHigh }}</div>
      </div>
      <div class="stat-card success">
        <div class="stat-label">已修复率</div>
        <div class="stat-value">{{ stats.fixRate }}%</div>
      </div>
    </div>

    <!-- Severity Bar Chart -->
    <div class="card" style="padding: 16px; margin-bottom: 16px;">
      <h3 style="margin-bottom: 16px; color: var(--rs-text-primary);">漏洞等级分布</h3>
      <div style="display: flex; align-items: flex-end; gap: 24px; height: 140px; padding: 0 20px;">
        <div v-for="bar in sevBars" :key="bar.label" style="flex: 1; display: flex; flex-direction: column; align-items: center;">
          <div style="font-size: 14px; font-weight: bold; margin-bottom: 4px;" :style="{ color: bar.color }">{{ bar.count }}</div>
          <div :style="{ width: '100%', maxWidth: '60px', height: bar.height + 'px', background: bar.color, borderRadius: '4px 4px 0 0', transition: 'height 0.3s' }" />
          <div style="font-size: 11px; color: var(--rs-text-secondary); margin-top: 6px;">{{ bar.label }}</div>
        </div>
      </div>
    </div>

    <!-- Active Scans + Quick Actions -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
      <div class="card" style="padding: 16px;">
        <h3 style="margin-bottom: 12px; color: var(--rs-text-primary);">运行中的扫描</h3>
        <div v-for="s in activeScans" :key="s.id" style="padding: 8px 0; border-bottom: 1px solid var(--rs-border);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div>{{ s.task_name }}</div>
              <div style="font-size: 12px; color: var(--rs-text-secondary);">{{ s.scan_strategy }}</div>
            </div>
            <el-progress :percentage="s.progress" :stroke-width="6" style="width: 100px;" />
          </div>
        </div>
        <div v-if="!activeScans.length" style="text-align: center; padding: 20px; color: var(--rs-text-secondary); font-size: 13px;">
          当前没有运行中的扫描
        </div>
      </div>

      <div class="card" style="padding: 16px;">
        <h3 style="margin-bottom: 12px; color: var(--rs-text-primary);">系统状态</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div style="padding: 12px; background: var(--rs-bg-secondary); border-radius: 6px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">数据库</div>
            <div style="font-size: 14px; margin-top: 4px;">
              <span :style="{ color: health.database === 'ok' ? 'var(--rs-success)' : 'var(--rs-danger)' }">
                {{ health.database === 'ok' ? '正常' : '异常' }}
              </span>
            </div>
          </div>
          <div style="padding: 12px; background: var(--rs-bg-secondary); border-radius: 6px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">Redis</div>
            <div style="font-size: 14px; margin-top: 4px;">
              <span :style="{ color: health.redis === 'ok' ? 'var(--rs-success)' : 'var(--rs-danger)' }">
                {{ health.redis === 'ok' ? '正常' : '异常' }}
              </span>
            </div>
          </div>
          <div style="padding: 12px; background: var(--rs-bg-secondary); border-radius: 6px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">插件数</div>
            <div style="font-size: 14px; margin-top: 4px;">{{ stats.pluginCount }}</div>
          </div>
          <div style="padding: 12px; background: var(--rs-bg-secondary); border-radius: 6px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">待处理工单</div>
            <div style="font-size: 14px; margin-top: 4px;">{{ stats.pendingOrders }}</div>
          </div>
        </div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
      <div class="card">
        <h3 style="margin-bottom: 16px; color: var(--rs-text-primary);">最近项目</h3>
        <div v-for="p in recentProjects" :key="p.id"
          style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--rs-border); cursor: pointer;"
          @click="$router.push(`/projects/${p.id}`)">
          <div>
            <div>{{ p.name }}</div>
            <div style="font-size: 12px; color: var(--rs-text-secondary);">{{ p.client_name || p.mode }}</div>
          </div>
          <div style="text-align: right;">
            <span class="severity-badge" :class="p.mode === 'combat' ? 'critical' : p.mode === 'range' ? 'medium' : 'low'">
              {{ {combat: '实战', range: '靶场', research: '研究'}[p.mode] }}
            </span>
          </div>
        </div>
        <el-empty v-if="!recentProjects.length" description="暂无项目" />
      </div>

      <div class="card">
        <h3 style="margin-bottom: 16px; color: var(--rs-text-primary);">最新漏洞情报</h3>
        <div v-for="v in latestVulns" :key="v.id"
          style="padding: 10px 0; border-bottom: 1px solid var(--rs-border);">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="severity-badge" :class="v.severity">{{ v.severity }}</span>
            <span>{{ v.title }}</span>
          </div>
          <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">
            {{ v.cve_id || v.cnvd_id }} · {{ v.affected_software }}
          </div>
        </div>
        <el-empty v-if="!latestVulns.length" description="暂无情报" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../stores/api'

const stats = ref({ activeProjects: 0, totalFindings: 0, criticalHigh: 0, fixRate: 0, pluginCount: 0, pendingOrders: 0 })
const sevCounts = ref({ critical: 0, high: 0, medium: 0, low: 0, info: 0 })
const recentProjects = ref([])
const latestVulns = ref([])
const activeScans = ref([])
const health = ref({ database: 'ok', redis: 'ok' })

const sevBars = computed(() => {
  const max = Math.max(...Object.values(sevCounts.value), 1)
  return [
    { label: '严重', count: sevCounts.value.critical, color: '#e74c3c', height: Math.round(sevCounts.value.critical / max * 100) },
    { label: '高危', count: sevCounts.value.high, color: '#e67e22', height: Math.round(sevCounts.value.high / max * 100) },
    { label: '中危', count: sevCounts.value.medium, color: '#f1c40f', height: Math.round(sevCounts.value.medium / max * 100) },
    { label: '低危', count: sevCounts.value.low, color: '#3498db', height: Math.round(sevCounts.value.low / max * 100) },
    { label: '信息', count: sevCounts.value.info, color: '#95a5a6', height: Math.round(sevCounts.value.info / max * 100) },
  ]
})

onMounted(async () => {
  const tasks = []

  tasks.push(api.get('/projects', { params: { status: 'active' } }).then(res => {
    const items = res.items || []
    recentProjects.value = items.slice(0, 5)
    stats.value.activeProjects = items.length

    // Aggregate findings stats across projects
    let totalFindings = 0, critHigh = 0, fixed = 0
    const scanPromises = []
    for (const p of items) {
      scanPromises.push(
        api.get(`/projects/${p.id}/findings/stats`).then(st => {
          const sevs = st.severities || {}
          totalFindings += Object.values(sevs).reduce((a, b) => a + b, 0)
          critHigh += (sevs.critical || 0) + (sevs.high || 0)
          fixed += st.fixed || 0
          sevCounts.value.critical += sevs.critical || 0
          sevCounts.value.high += sevs.high || 0
          sevCounts.value.medium += sevs.medium || 0
          sevCounts.value.low += sevs.low || 0
          sevCounts.value.info += sevs.info || 0
        }).catch(() => {})
      )
      scanPromises.push(
        api.get(`/projects/${p.id}/scans`).then(sr => {
          const running = (sr.items || []).filter(s => s.status === 'running')
          activeScans.value.push(...running)
        }).catch(() => {})
      )
    }
    return Promise.all(scanPromises).then(() => {
      stats.value.totalFindings = totalFindings
      stats.value.criticalHigh = critHigh
      stats.value.fixRate = totalFindings > 0 ? Math.round(fixed / totalFindings * 100) : 0
    })
  }).catch(() => {}))

  tasks.push(api.get('/knowledge', { params: { limit: 5 } }).then(res => {
    latestVulns.value = res.items || []
  }).catch(() => {}))

  tasks.push(api.get('/health').then(res => {
    health.value = res
  }).catch(() => {}))

  tasks.push(api.get('/plugins').then(res => {
    stats.value.pluginCount = (res.items || []).length
  }).catch(() => {}))

  tasks.push(api.get('/workflow', { params: { status: 'pending' } }).then(res => {
    stats.value.pendingOrders = (res.items || []).length
  }).catch(() => {}))

  await Promise.all(tasks)
})
</script>
