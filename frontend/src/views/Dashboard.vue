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
import { ref, onMounted } from 'vue'
import api from '../stores/api'

const stats = ref({ activeProjects: 0, totalFindings: 0, criticalHigh: 0, fixRate: 0 })
const recentProjects = ref([])
const latestVulns = ref([])

onMounted(async () => {
  try {
    const res = await api.get('/projects', { params: { status: 'active' } })
    recentProjects.value = (res.items || []).slice(0, 5)
    stats.value.activeProjects = res.items?.length || 0
  } catch (e) { /* empty */ }

  try {
    const res = await api.get('/knowledge', { params: { limit: 5 } })
    latestVulns.value = res.items || []
  } catch (e) { /* empty */ }
})
</script>
