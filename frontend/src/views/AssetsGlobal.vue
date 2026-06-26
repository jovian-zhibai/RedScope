<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>资产管理 <span style="font-size: 14px; color: var(--rs-text-secondary); font-weight: normal;">{{ total }} 个资产</span></h2>
      <el-input v-model="searchText" placeholder="搜索主机/IP..." size="small" style="width: 240px;" @input="onSearch" />
    </div>

    <el-table :data="assets" style="width: 100%;" @row-click="goToAsset">
      <el-table-column prop="project_name" label="项目" width="140" />
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
    <el-empty v-if="!assets.length && !loading" description="暂无资产" />
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../stores/api'

const router = useRouter()
const assets = ref([])
const total = ref(0)
const loading = ref(false)
const searchText = ref('')
let searchTimer = null

const load = async () => {
  loading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    const r = await api.get('/global/assets', { params })
    assets.value = r.items || []
    total.value = r.total || 0
  } catch { assets.value = [] }
  finally { loading.value = false }
}

const onSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}

const goToAsset = (row) => { router.push(`/projects/${row.project_id}/assets`) }

onMounted(load)
</script>
