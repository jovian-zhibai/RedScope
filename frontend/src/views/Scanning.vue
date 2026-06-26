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

    <el-table :data="tasks" style="width: 100%;" @row-click="openDetail">
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
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="{pending:'info',running:'warning',completed:'success',failed:'danger',stopped:'danger'}[row.status]" size="small">
            {{ {pending:'排队中',running:'扫描中',completed:'已完成',failed:'失败',stopped:'已停止'}[row.status] }}
          </el-tag>
          <div v-if="row.status === 'failed' && row.vulns_found === 0" style="font-size: 11px; color: var(--rs-danger); margin-top: 2px;">点击查看原因</div>
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

    <!-- Scan Detail Drawer -->
    <el-drawer v-model="showDetail" :title="detailScan?.task_name || '扫描详情'" size="600px">
      <div v-if="detailScan" style="padding: 0 8px;">
        <div class="stat-grid" style="margin-bottom: 16px;">
          <div class="stat-card info"><div class="stat-label">状态</div><div class="stat-value" style="font-size: 16px;">
            <el-tag :type="{pending:'info',running:'warning',completed:'success',failed:'danger',stopped:'danger'}[detailScan.status]">
              {{ {pending:'等待中',running:'运行中',completed:'已完成',failed:'失败',stopped:'已停止'}[detailScan.status] }}
            </el-tag>
          </div></div>
          <div class="stat-card warning"><div class="stat-label">进度</div><div class="stat-value" style="font-size: 16px;">{{ detailScan.scanned_count || 0 }} / {{ detailScan.total_targets || 0 }}</div></div>
          <div class="stat-card critical"><div class="stat-label">发现漏洞</div><div class="stat-value">{{ detailScan.vulns_found || 0 }}</div></div>
        </div>

        <div v-if="detailScan.progress < 100 && detailScan.status === 'running'" style="margin-bottom: 16px;">
          <el-progress :percentage="detailScan.progress" :stroke-width="10" />
        </div>

        <h4 style="margin: 16px 0 8px;">扫描引擎</h4>
        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px;">
          <el-tag v-for="e in (detailScan.engines || [])" :key="e" size="small">{{ e }}</el-tag>
          <el-tag v-if="!detailScan.engines?.length" size="small" type="info">自动</el-tag>
        </div>

        <h4 style="margin: 16px 0 8px;">扫描目标</h4>
        <div style="max-height: 150px; overflow-y: auto; background: var(--rs-bg-secondary); padding: 8px 12px; border-radius: 6px; margin-bottom: 12px;">
          <div v-for="t in (detailScan.target_assets || [])" :key="t" style="font-size: 12px; font-family: monospace; padding: 2px 0;">{{ t }}</div>
          <div v-if="!detailScan.target_assets?.length" style="color: var(--rs-text-secondary); font-size: 12px;">无目标</div>
        </div>

        <h4 style="margin: 16px 0 8px;">时间</h4>
        <div style="font-size: 13px; color: var(--rs-text-secondary);">
          <div>开始: {{ detailScan.started_at?.replace('T', ' ').slice(0, 19) || '未开始' }}</div>
          <div>结束: {{ detailScan.finished_at?.replace('T', ' ').slice(0, 19) || '进行中' }}</div>
        </div>

        <!-- Engine Runs Detail -->
        <div v-if="detailScan.engine_runs?.length" style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px;">引擎执行详情</h4>
          <div v-for="r in detailScan.engine_runs" :key="r.id" style="padding: 10px; margin-bottom: 6px; background: var(--rs-bg-secondary); border-radius: 6px; border-left: 3px solid" :style="{ borderLeftColor: r.status === 'completed' ? 'var(--rs-success)' : r.status === 'failed' ? 'var(--rs-danger)' : 'var(--rs-warning)' }">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <strong style="font-size: 13px;">{{ r.engine_name }}</strong>
              <el-tag :type="r.status === 'completed' ? 'success' : r.status === 'failed' ? 'danger' : 'warning'" size="small">{{ {completed:'完成',failed:'失败',running:'运行中'}[r.status] || r.status }}</el-tag>
            </div>
            <div v-if="r.vulns_found" style="font-size: 12px; color: var(--rs-danger); margin-top: 4px;">发现 {{ r.vulns_found }} 个漏洞</div>
            <div v-if="r.error_message" style="font-size: 12px; color: var(--rs-warning); margin-top: 4px; white-space: pre-wrap;">{{ r.error_message }}</div>
            <el-button v-if="r.runner_job_id" size="small" text style="margin-top: 4px; font-size: 11px;" @click="loadLogs(r.runner_job_id)">查看日志</el-button>
          </div>
        </div>
        <div v-else-if="detailScan.status === 'completed' || detailScan.status === 'failed'" style="margin-top: 16px; padding: 12px; background: var(--rs-bg-secondary); border-radius: 6px; border-left: 3px solid var(--rs-warning);">
          <div style="font-size: 13px; color: var(--rs-warning);">无引擎执行记录。可能原因: Celery Worker 未启动、插件未加载、或 scan-runner 服务未运行。</div>
        </div>

        <div v-if="detailScan.vulns_found > 0" style="margin-top: 16px;">
          <el-button type="primary" size="small" @click="$router.push(`/projects/${pid}/findings`); showDetail = false">查看发现的漏洞 →</el-button>
        </div>
        <div v-else-if="detailScan.status === 'completed'" style="margin-top: 16px; padding: 12px; background: var(--rs-bg-secondary); border-radius: 6px; border-left: 3px solid var(--rs-warning);">
          <div style="font-size: 13px; color: var(--rs-warning); margin-bottom: 4px;">扫描完成但未发现漏洞</div>
          <div style="font-size: 12px; color: var(--rs-text-secondary);">可能原因：目标不可达、目标无已知漏洞、或扫描引擎配置问题。请检查上方引擎执行详情中的错误信息。</div>
        </div>

        <div v-if="detailScan.status === 'running'" style="margin-top: 16px;">
          <el-button type="danger" size="small" @click="stopScan(detailScan.id); showDetail = false">停止扫描</el-button>
        </div>

        <div v-if="scanLogs" style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px;">扫描日志</h4>
          <pre style="font-size: 11px; background: var(--rs-bg-secondary); padding: 12px; border-radius: 6px; overflow: auto; max-height: 300px; white-space: pre-wrap; word-break: break-all;">{{ scanLogs }}</pre>
        </div>
      </div>
    </el-drawer>

    <!-- Create Scan Dialog -->
    <el-dialog v-model="showCreate" title="新建扫描任务" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务名称"><el-input v-model="form.task_name" placeholder="可选，自动生成" /></el-form-item>
        <el-form-item label="扫描策略">
          <el-radio-group v-model="form.scan_strategy" @change="onStrategyChange">
            <el-radio-button value="quick">快速扫描</el-radio-button>
            <el-radio-button value="standard">标准扫描</el-radio-button>
            <el-radio-button value="deep">深度扫描</el-radio-button>
          </el-radio-group>
          <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">
            {{ {quick:'nmap 端口扫描，速度最快',standard:'nmap + nuclei 端口+漏洞扫描',deep:'nmap + nuclei + httpx + dirsearch 全量扫描，耗时较长'}[form.scan_strategy] }}
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
import { logSessionActivity } from '../stores/api'

const route = useRoute()
const pid = route.params.id
const tasks = ref([])
const showCreate = ref(false)
const creating = ref(false)
const refreshing = ref(false)
const availableEngines = ref([])
const showDetail = ref(false)
const detailScan = ref(null)
const scanLogs = ref('')
const form = ref({ task_name: '', scan_strategy: 'standard', engines: ['nmap', 'nuclei'], targetsText: '' })

const strategyEngines = { quick: ['nmap'], standard: ['nmap', 'nuclei'], deep: ['nmap', 'nuclei', 'httpx', 'dirsearch'] }
const onStrategyChange = () => { form.value.engines = [...(strategyEngines[form.value.scan_strategy] || [])] }

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
      task_name: form.value.task_name || `${form.value.scan_strategy}扫描 - ${new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`,
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
    logSessionActivity(pid, '创建扫描', `${payload.scan_strategy} 策略, ${targets.length} 个目标`)
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

const openDetail = async (row) => {
  scanLogs.value = ''
  try {
    detailScan.value = await api.get(`/projects/${pid}/scans/${row.id}`)
  } catch {
    detailScan.value = row
  }
  showDetail.value = true
}

const loadLogs = async (jobId) => {
  try {
    const res = await api.get(`/projects/${pid}/scans/${detailScan.value.id}/logs/${jobId}`)
    scanLogs.value = (res.stderr || '') + (res.stdout ? '\n--- stdout ---\n' + res.stdout : '')
  } catch { scanLogs.value = '无法加载日志' }
}

onMounted(async () => {
  await Promise.all([load(), loadEngines()])
  pollTimer = setInterval(() => {
    if (tasks.value.some(t => t.status === 'running' || t.status === 'pending')) load()
  }, 5000)
})

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>
