<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>漏洞管理</h2>
      <el-select v-model="pid" placeholder="选择项目" size="small" style="width: 240px;" @change="load">
        <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name" />
      </el-select>
    </div>
    <div v-if="!pid" style="text-align: center; padding: 60px; color: var(--rs-text-secondary);">请先选择一个项目</div>
    <div v-else>
      <div style="margin-bottom: 12px;">
        <el-button type="primary" size="small" @click="$router.push(`/projects/${pid}/findings`)">详细管理 →</el-button>
      </div>
      <div class="stat-grid">
        <div class="stat-card critical"><div class="stat-label">严重</div><div class="stat-value">{{ stats.critical || 0 }}</div></div>
        <div class="stat-card warning"><div class="stat-label">高危</div><div class="stat-value">{{ stats.high || 0 }}</div></div>
        <div class="stat-card info"><div class="stat-label">中危</div><div class="stat-value">{{ stats.medium || 0 }}</div></div>
        <div class="stat-card success"><div class="stat-label">已修复</div><div class="stat-value">{{ stats.fixed || 0 }}</div></div>
      </div>
      <el-table :data="findings" style="width: 100%;">
        <el-table-column prop="title" label="漏洞" min-width="250" />
        <el-table-column prop="severity" label="等级" width="80"><template #default="{ row }"><span class="severity-badge" :class="row.severity">{{ row.severity }}</span></template></el-table-column>
        <el-table-column prop="fix_status" label="状态" width="100">
          <template #default="{ row }"><el-tag :type="row.fix_status === 'fixed' ? 'success' : 'danger'" size="small">{{ {unfixed:'未修复',fixing:'修复中',fixed:'已修复'}[row.fix_status] }}</el-tag></template>
        </el-table-column>
      </el-table>
      <el-pagination v-if="total > pageSize" :current-page="currentPage" :page-size="pageSize" :total="total" @current-change="(p) => { currentPage = p; load() }" layout="prev, pager, next, total" style="margin-top: 12px; justify-content: flex-end;" />
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import api from '../stores/api'
const projects = ref([]); const pid = ref(null); const findings = ref([]); const stats = ref({})
const total = ref(0); const currentPage = ref(1); const pageSize = ref(20)
onMounted(async () => { try { const r = await api.get('/projects'); projects.value = r.items || [] } catch {} })
const load = async () => {
  if (!pid.value) return
  try {
    const [f, s] = await Promise.all([
      api.get(`/projects/${pid.value}/findings`, { params: { page: currentPage.value, page_size: pageSize.value } }),
      api.get(`/projects/${pid.value}/findings/stats`),
    ])
    findings.value = f.items || []; total.value = f.total || 0
    stats.value = { ...s.severities, fixed: s.fixed }
  } catch {}
}
</script>
