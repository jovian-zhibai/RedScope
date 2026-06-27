<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>扫描任务</h2>
      <el-button size="small" @click="load" :loading="loading">刷新</el-button>
    </div>

    <el-table :data="tasks" style="width: 100%;" @row-click="goToScan">
      <el-table-column prop="project_name" label="项目" width="160" />
      <el-table-column prop="task_name" label="任务" min-width="200" />
      <el-table-column prop="scan_strategy" label="策略" width="80">
        <template #default="{ row }">
          <el-tag size="small">{{ {quick:'快速',standard:'标准',deep:'深度',passive:'被动'}[row.scan_strategy] || row.scan_strategy }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="引擎" width="150">
        <template #default="{ row }">
          <div style="display: flex; gap: 3px; flex-wrap: wrap;">
            <el-tag v-for="e in (row.engines || []).slice(0, 3)" :key="e" size="small" type="info">{{ e }}</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="{pending:'info',running:'warning',completed:'success',failed:'danger',stopped:'danger'}[row.status]" size="small">
            {{ {pending:'等待中',running:'运行中',completed:'已完成',failed:'失败',stopped:'已停止'}[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="progress" label="进度" width="100">
        <template #default="{ row }"><el-progress :percentage="row.progress" :stroke-width="6" /></template>
      </el-table-column>
      <el-table-column label="目标/漏洞" width="100">
        <template #default="{ row }">
          <span style="font-size: 12px;">{{ row.scanned_count || 0 }}/{{ row.total_targets || 0 }}</span>
          <span v-if="row.vulns_found" style="color: var(--rs-danger); margin-left: 4px; font-size: 12px;">{{ row.vulns_found }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="120">
        <template #default="{ row }">{{ row.created_at?.split('T')[0] }}</template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!tasks.length && !loading" description="暂无扫描任务" />
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../stores/api'
import { useVersionPrefix } from '../composables/useVersionPrefix'

const router = useRouter()
const { p } = useVersionPrefix()
const tasks = ref([])
const loading = ref(false)

const load = async () => {
  loading.value = true
  try { const r = await api.get('/global/scans'); tasks.value = r.items || [] }
  catch { tasks.value = [] }
  finally { loading.value = false }
}

const goToScan = (row) => { router.push(p(`/projects/${row.project_id}/scanning`)) }

onMounted(load)
</script>
