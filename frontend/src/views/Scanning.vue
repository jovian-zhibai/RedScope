<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>扫描任务</h2>
      <el-button type="primary" size="small" @click="showCreate = true"><el-icon><VideoPlay /></el-icon> 新建扫描</el-button>
    </div>
    <el-table :data="tasks" style="width: 100%;">
      <el-table-column prop="task_name" label="任务名称" min-width="200" />
      <el-table-column prop="scan_strategy" label="策略" width="100" />
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
      <el-table-column prop="vulns_found" label="发现漏洞" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="120">
        <template #default="{ row }">{{ row.created_at?.split('T')[0] }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button v-if="row.status === 'running'" type="danger" size="small" @click="stopScan(row.id)">停止</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="新建扫描任务" width="520px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务名称"><el-input v-model="form.task_name" /></el-form-item>
        <el-form-item label="扫描策略">
          <el-radio-group v-model="form.scan_strategy">
            <el-radio-button value="quick">快速</el-radio-button>
            <el-radio-button value="standard">标准</el-radio-button>
            <el-radio-button value="deep">深度</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="目标">
          <el-input v-model="form.targetsText" type="textarea" :rows="4" placeholder="每行一个目标 (IP/域名/URL)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createScan">开始扫描</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const route = useRoute()
const pid = route.params.id
const tasks = ref([])
const showCreate = ref(false)
const form = ref({ task_name: '', scan_strategy: 'standard', targetsText: '' })

const load = async () => { const res = await api.get(`/projects/${pid}/scans`); tasks.value = res.items || [] }

const createScan = async () => {
  const targets = form.value.targetsText.split('\n').map(s => s.trim()).filter(Boolean)
  try {
    const res = await api.post(`/projects/${pid}/scans`, { task_name: form.value.task_name, scan_strategy: form.value.scan_strategy, targets })
    showCreate.value = false
    const allWarnings = []
    if (res.cloud_warnings?.length) allWarnings.push(...res.cloud_warnings.map(w => `☁️ ${w.provider}: ${w.notice}`))
    if (res.opsec_warnings?.length) allWarnings.push(...res.opsec_warnings.map(w => `⚠️ ${w.message}\n   → ${w.suggestion}`))
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
  }
}

const stopScan = async (id) => { await api.post(`/projects/${pid}/scans/${id}/stop`); ElMessage.success('已停止'); await load() }

onMounted(load)
</script>
