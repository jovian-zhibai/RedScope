<template>
  <div>
    <!-- Quick Actions -->
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px;">
      <div class="card onboard-step" @click="quickCreate">
        <div style="font-size: 20px; margin-bottom: 6px;">🚀</div>
        <div style="font-weight: 600; font-size: 13px;">新建项目</div>
      </div>
      <div class="card onboard-step" @click="$router.push('/scans')">
        <div style="font-size: 20px; margin-bottom: 6px;">🔍</div>
        <div style="font-weight: 600; font-size: 13px;">开始扫描</div>
      </div>
      <div class="card onboard-step" @click="$router.push('/ai')">
        <div style="font-size: 20px; margin-bottom: 6px;">🤖</div>
        <div style="font-weight: 600; font-size: 13px;">AI 助手</div>
      </div>
      <div class="card onboard-step" @click="$router.push('/warroom')">
        <div style="font-size: 20px; margin-bottom: 6px;">🎯</div>
        <div style="font-weight: 600; font-size: 13px;">作战管理</div>
      </div>
    </div>

    <!-- Stats -->
    <div class="stat-grid">
      <div class="stat-card info"><div class="stat-label">活跃项目</div><div class="stat-value">{{ stats.activeProjects }}</div></div>
      <div class="stat-card warning"><div class="stat-label">发现漏洞</div><div class="stat-value">{{ stats.totalFindings }}</div></div>
      <div class="stat-card critical"><div class="stat-label">严重/高危</div><div class="stat-value">{{ stats.criticalHigh }}</div></div>
      <div class="stat-card success"><div class="stat-label">修复率</div><div class="stat-value">{{ stats.fixRate }}%</div></div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
      <!-- Running Scans -->
      <div class="card">
        <h3 style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
          <span>运行中的扫描</span>
          <el-button size="small" text @click="$router.push('/scans')">查看全部</el-button>
        </h3>
        <div v-for="s in activeScans" :key="s.id" style="padding: 10px 0; border-bottom: 1px solid var(--rs-border);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-size: 13px;">{{ s.task_name }}</div>
              <div style="font-size: 11px; color: var(--rs-text-secondary);">{{ s.scan_strategy }}</div>
            </div>
            <el-progress :percentage="s.progress" :stroke-width="6" style="width: 80px;" />
          </div>
        </div>
        <div v-if="!activeScans.length" style="text-align: center; padding: 20px; color: var(--rs-text-secondary); font-size: 13px;">
          暂无运行中的扫描
        </div>
      </div>

      <!-- Recent Projects -->
      <div class="card">
        <h3 style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
          <span>项目</span>
          <el-button size="small" text @click="$router.push('/projects')">管理</el-button>
        </h3>
        <div v-for="p in recentProjects" :key="p.id"
          style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--rs-border); cursor: pointer;"
          @click="$router.push(`/projects/${p.id}`)">
          <div>
            <div style="font-size: 13px;">{{ p.name }}</div>
            <div style="font-size: 11px; color: var(--rs-text-secondary);">{{ p.client_name || '' }} · 资产 {{ p.asset_count }} · 漏洞 {{ p.finding_count }}</div>
          </div>
          <span class="severity-badge" :class="p.mode === 'combat' ? 'critical' : p.mode === 'range' ? 'medium' : 'low'">
            {{ {combat: '实战', range: '靶场', research: '研究'}[p.mode] }}
          </span>
        </div>
        <el-empty v-if="!recentProjects.length" description="暂无项目" :image-size="40" />
      </div>
    </div>

    <!-- System Status -->
    <div class="card" style="margin-top: 16px;">
      <h3 style="margin-bottom: 12px;">系统状态</h3>
      <div style="display: flex; gap: 24px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span :style="{ color: health.database === 'ok' ? 'var(--rs-success)' : 'var(--rs-danger)' }">●</span>
          数据库 {{ health.database === 'ok' ? '正常' : '异常' }}
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span :style="{ color: health.redis === 'ok' ? 'var(--rs-success)' : 'var(--rs-danger)' }">●</span>
          Redis {{ health.redis === 'ok' ? '正常' : '异常' }}
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="color: var(--rs-info);">●</span>
          工具 {{ stats.pluginCount }} 个
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../stores/api'

const router = useRouter()

const stats = ref({ activeProjects: 0, totalFindings: 0, criticalHigh: 0, fixRate: 0, pluginCount: 0 })
const recentProjects = ref([])
const activeScans = ref([])
const health = ref({ database: 'ok', redis: 'ok' })

const quickCreate = () => { router.push('/projects?action=create') }

onMounted(async () => {
  const tasks = []

  tasks.push(api.get('/projects').then(res => {
    const items = res.items || []
    recentProjects.value = items.slice(0, 6)
    stats.value.activeProjects = items.length

    let totalFindings = 0, critHigh = 0, fixed = 0
    const subTasks = []
    for (const p of items) {
      subTasks.push(api.get(`/projects/${p.id}/findings/stats`).then(st => {
        const sevs = st.severities || {}
        totalFindings += Object.values(sevs).reduce((a, b) => a + b, 0)
        critHigh += (sevs.critical || 0) + (sevs.high || 0)
        fixed += st.fixed || 0
      }).catch(() => {}))
      subTasks.push(api.get(`/projects/${p.id}/scans`).then(sr => {
        activeScans.value.push(...(sr.items || []).filter(s => s.status === 'running'))
      }).catch(() => {}))
    }
    return Promise.all(subTasks).then(() => {
      stats.value.totalFindings = totalFindings
      stats.value.criticalHigh = critHigh
      stats.value.fixRate = totalFindings > 0 ? Math.round(fixed / totalFindings * 100) : 0
    })
  }).catch(() => {}))

  tasks.push(api.get('/health').then(r => { health.value = r }).catch(() => {}))
  tasks.push(api.get('/plugins').then(r => { stats.value.pluginCount = (r.items || []).length }).catch(() => {}))

  await Promise.all(tasks)
})
</script>
