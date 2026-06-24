<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>扫描任务</h2>
      <div style="display: flex; gap: 8px;">
        <el-button size="small" @click="load" :loading="refreshing">刷新</el-button>
        <el-button type="primary" size="small" @click="showCreate = true"><el-icon><VideoPlay /></el-icon> 新建扫描</el-button>
      </div>
    </div>

    <!-- Stats -->
    <div class="stat-grid" style="margin-bottom: 16px;">
      <div class="stat-card info"><div class="stat-label">总任务</div><div class="stat-value">{{ tasks.length }}</div></div>
      <div class="stat-card warning"><div class="stat-label">运行中</div><div class="stat-value">{{ tasks.filter(t => t.status === 'running').length }}</div></div>
      <div class="stat-card success"><div class="stat-label">已完成</div><div class="stat-value">{{ tasks.filter(t => t.status === 'completed').length }}</div></div>
      <div class="stat-card critical"><div class="stat-label">发现漏洞</div><div class="stat-value">{{ tasks.reduce((a, t) => a + (t.vulns_found || 0), 0) }}</div></div>
    </div>

    <el-table :data="tasks" style="width: 100%;" @row-click="toggleDetail">
      <el-table-column prop="task_name" label="任务名称" min-width="200" />
      <el-table-column prop="scan_strategy" label="策略" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ {quick:'快速',standard:'标准',deep:'深度'}[row.scan_strategy] || row.scan_strategy }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="引擎" width="180">
        <template #default="{ row }">
          <div style="display: flex; gap: 4px; flex-wrap: wrap;">
            <el-tag v-for="e in (row.engines || [])" :key="e" size="small" type="info">{{ e }}</el-tag>
            <span v-if="!row.engines?.length" style="color: var(--rs-text-secondary); font-size: 12px;">自动</span>
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
      <el-table-column prop="progress" label="进度" width="120">
        <template #default="{ row }"><el-progress :percentage="row.progress" :stroke-width="6" /></template>
      </el-table-column>
      <el-table-column label="目标/漏洞" width="100">
        <template #default="{ row }">
          <span style="font-size: 12px;">{{ row.scanned_count || 0 }}/{{ row.total_targets || 0 }}</span>
          <span v-if="row.vulns_found" style="color: var(--rs-danger); margin-left: 4px; font-size: 12px;">🔴{{ row.vulns_found }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="120">
        <template #default="{ row }">{{ row.created_at?.split('T')[0] }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button v-if="row.status === 'running'" type="danger" size="small" @click.stop="stopScan(row.id)">停止</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create Scan Dialog -->
    <el-dialog v-model="showCreate" title="新建扫描任务" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务名称"><el-input v-model="form.task_name" placeholder="可选，自动生成" /></el-form-item>
        <el-form-item label="扫描策略">
          <el-radio-group v-model="form.scan_strategy">
            <el-radio-button value="quick">快速扫描</el-radio-button>
            <el-radio-button value="standard">标准扫描</el-radio-button>
            <el-radio-button value="deep">深度扫描</el-radio-button>
          </el-radio-group>
          <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">
            {{ {quick:'仅端口扫描，速度最快',standard:'端口+指纹+漏洞匹配',deep:'全量扫描+POC验证，耗时较长'}[form.scan_strategy] }}
          </div>
        </el-form-item>
        <el-form-item label="扫描引擎">
          <el-checkbox-group v-model="form.engines">
            <el-checkbox v-for="eng in availableEngines" :key="eng.name" :value="eng.name">
              <span>{{ eng.display_name }}</span>
              <span style="font-size: 11px; color: var(--rs-text-secondary); margin-left: 4px;">({{ eng.category }})</span>
            </el-checkbox>
          </el-checkbox-group>
          <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">
            不选则根据策略自动选择引擎
          </div>
        </el-form-item>
        <el-form-item label="目标">
          <el-input v-model="form.targetsText" type="textarea" :rows="5" placeholder="每行一个目标 (IP/域名/URL/CIDR)&#10;例:&#10;192.168.1.0/24&#10;example.com&#10;10.0.0.1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createScan" :loading="creating">开始扫描</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const route = useRoute()
const pid = route.params.id
const tasks = ref([])
const showCreate = ref(false)
const creating = ref(false)
const refreshing = ref(false)
const availableEngines = ref([])
const form = ref({ task_name: '', scan_strategy: 'standard', engines: [], targetsText: '' })

let pollTimer = null

const load = async () => {
  refreshing.value = true
  try {
    const res = await api.get(`/projects/${pid}/scans`)
    tasks.value = res.items || []
  } finally { refreshing.value = false }
}

const loadEngines = async () => {
  try {
    const res = await api.get('/plugins')
    availableEngines.value = (res.items || []).filter(p => p.is_enabled)
  } catch (e) { /* empty */ }
}

const createScan = async () => {
  const targets = form.value.targetsText.split('\n').map(s => s.trim()).filter(Boolean)
  if (!targets.length) { ElMessage.warning('请输入至少一个目标'); return }
  creating.value = true
  try {
    const payload = {
      task_name: form.value.task_name,
      scan_strategy: form.value.scan_strategy,
      targets,
    }
    if (form.value.engines.length) payload.engines = form.value.engines
    const res = await api.post(`/projects/${pid}/scans`, payload)
    showCreate.value = false
    form.value = { task_name: '', scan_strategy: 'standard', engines: [], targetsText: '' }
    const allWarnings = []
    if (res.cloud_warnings?.length) allWarnings.push(...res.cloud_warnings.map(w => `${w.provider}: ${w.notice}`))
    if (res.opsec_warnings?.length) allWarnings.push(...res.opsec_warnings.map(w => `${w.message} → ${w.suggestion}`))
    if (allWarnings.length > 0) {
      ElMessage.warning({ message: `扫描已创建。注意:\n${allWarnings.join('\n')}`, duration: 15000, showClose: true })
    } else {
      ElMessage.success('扫描任务已创建')
    }
    await load()
  } catch (e) {
    const detail = e.response?.data?.detail
    if (detail?.violations) { ElMessage.error(`目标越界: ${detail.violations.map(v => v.target + ' - ' + v.reason).join('; ')}`) }
    else { ElMessage.error(detail?.message || '创建失败') }
  } finally { creating.value = false }
}

const stopScan = async (id) => {
  await api.post(`/projects/${pid}/scans/${id}/stop`)
  ElMessage.success('已停止')
  await load()
}

const toggleDetail = (row) => {
  // Future: expand row to show engine runs detail
}

onMounted(async () => {
  await Promise.all([load(), loadEngines()])
  pollTimer = setInterval(() => {
    if (tasks.value.some(t => t.status === 'running')) load()
  }, 5000)
})

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>
