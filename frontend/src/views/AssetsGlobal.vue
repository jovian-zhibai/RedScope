<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>资产管理</h2>
      <el-select v-model="selectedProject" placeholder="选择项目" size="small" style="width: 240px;" @change="currentPage = 1; loadAssets()">
        <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name" />
      </el-select>
    </div>

    <div v-if="!selectedProject" style="text-align: center; padding: 60px; color: var(--rs-text-secondary);">
      请先选择一个项目来查看和管理资产
    </div>

    <div v-else>
      <div class="stat-grid" style="margin-bottom: 16px;">
        <div class="stat-card info"><div class="stat-label">总资产</div><div class="stat-value">{{ total }}</div></div>
      </div>

      <div style="display: flex; gap: 8px; margin-bottom: 12px;">
        <el-button type="primary" size="small" @click="$router.push(`/projects/${selectedProject}/assets`)">详细管理 →</el-button>
        <el-button size="small" @click="$router.push(`/projects/${selectedProject}/scanning`)">对此项目扫描 →</el-button>
      </div>

      <el-table :data="assets" style="width: 100%;">
        <el-table-column prop="host" label="主机" min-width="180" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="application" label="应用" width="150" />
        <el-table-column prop="server" label="服务" width="120" />
        <el-table-column prop="importance" label="重要性" width="100">
          <template #default="{ row }">
            <span class="severity-badge" :class="row.importance === 'critical' ? 'critical' : row.importance === 'low' ? 'low' : 'medium'">
              {{ {critical:'核心', normal:'一般', low:'低'}[row.importance] || row.importance }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="is_alive" label="存活" width="70">
          <template #default="{ row }">{{ row.is_alive ? '🟢' : '🔴' }}</template>
        </el-table-column>
      </el-table>
      <el-pagination v-if="total > pageSize" :current-page="currentPage" :page-size="pageSize" :total="total" @current-change="(p) => { currentPage = p; loadAssets() }" layout="prev, pager, next, total" style="margin-top: 12px; justify-content: flex-end;" />
      <el-empty v-if="!assets.length" description="该项目暂无资产" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../stores/api'

const projects = ref([])
const selectedProject = ref(null)
const assets = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

onMounted(async () => {
  try { const res = await api.get('/projects'); projects.value = res.items || [] } catch {}
})

const loadAssets = async () => {
  if (!selectedProject.value) return
  try {
    const res = await api.get(`/projects/${selectedProject.value}/assets`, { params: { page: currentPage.value, page_size: pageSize.value } })
    assets.value = res.items || []
    total.value = res.total || 0
  } catch { assets.value = []; total.value = 0 }
}
</script>
