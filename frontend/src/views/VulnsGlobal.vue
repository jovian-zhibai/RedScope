<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>漏洞管理</h2>
      <div style="display: flex; gap: 8px;">
        <el-select v-model="filterSev" placeholder="等级" clearable size="small" style="width: 100px;" @change="load">
          <el-option value="critical" label="严重" /><el-option value="high" label="高危" />
          <el-option value="medium" label="中危" /><el-option value="low" label="低危" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="修复状态" clearable size="small" style="width: 120px;" @change="load">
          <el-option value="unfixed" label="未修复" /><el-option value="fixing" label="修复中" />
          <el-option value="fixed" label="已修复" />
        </el-select>
      </div>
    </div>

    <div class="stat-grid" style="margin-bottom: 16px;">
      <div class="stat-card critical"><div class="stat-label">严重</div><div class="stat-value">{{ stats.critical || 0 }}</div></div>
      <div class="stat-card" style="border-left: 3px solid var(--rs-warning);"><div class="stat-label">高危</div><div class="stat-value">{{ stats.high || 0 }}</div></div>
      <div class="stat-card info"><div class="stat-label">总计</div><div class="stat-value">{{ stats.total || 0 }}</div></div>
    </div>

    <el-table :data="findings" style="width: 100%;" @row-click="goToFinding">
      <el-table-column prop="project_name" label="项目" width="140" />
      <el-table-column prop="title" label="漏洞名称" min-width="250" />
      <el-table-column prop="severity" label="等级" width="80">
        <template #default="{ row }"><span class="severity-badge" :class="row.severity">{{ row.severity }}</span></template>
      </el-table-column>
      <el-table-column prop="vuln_type" label="类型" width="110" />
      <el-table-column prop="found_by" label="来源" width="100" />
      <el-table-column prop="fix_status" label="修复状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.fix_status === 'fixed' ? 'success' : row.fix_status === 'fixing' ? 'warning' : 'danger'" size="small">
            {{ {unfixed:'未修复', fixing:'修复中', fixed:'已修复', reopen:'复发'}[row.fix_status] || row.fix_status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="发现时间" width="120">
        <template #default="{ row }">{{ row.created_at?.split('T')[0] }}</template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!findings.length && !loading" description="暂无漏洞" />
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../stores/api'
import { useVersionPrefix } from '../composables/useVersionPrefix'

const router = useRouter()
const { p } = useVersionPrefix()
const findings = ref([])
const stats = ref({})
const loading = ref(false)
const filterSev = ref('')
const filterStatus = ref('')

const load = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterSev.value) params.severity = filterSev.value
    if (filterStatus.value) params.fix_status = filterStatus.value
    const r = await api.get('/global/findings', { params })
    findings.value = r.items || []
    stats.value = r.stats || {}
  } catch { findings.value = [] }
  finally { loading.value = false }
}

const goToFinding = (row) => { router.push(p(`/projects/${row.project_id}/findings`)) }

onMounted(load)
</script>
