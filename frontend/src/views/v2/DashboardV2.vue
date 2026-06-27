<template>
  <div>
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 4px; margin-bottom: 2px;">
      <div style="display: flex; gap: 2px;">
        <div class="v2-quick-action" @click="$emit('quick-create')">
          <el-icon><Plus /></el-icon> 新建项目
        </div>
        <div class="v2-quick-action" @click="showQuickScan = true">
          <el-icon><VideoPlay /></el-icon> 快速扫描
        </div>
        <div class="v2-quick-action" @click="$router.push('/v2/ai')">
          <el-icon><MagicStick /></el-icon> AI 助手
        </div>
        <div class="v2-quick-action" @click="$router.push('/v2/vulns')">
          <el-icon><Warning /></el-icon> 漏洞管理
        </div>
      </div>
      <span style="font-family: var(--rs2-mono); font-size: 9px; color: var(--rs2-text-muted); letter-spacing: 0.5px;">
        LAST SYNC: <span style="color: var(--rs2-text-secondary);">{{ lastSync }}</span>
      </span>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 2px; margin-bottom: 2px;">
      <div class="v2-panel" style="padding: 18px 16px;">
        <span class="v2-panel-tag accent">PROJ</span>
        <div style="padding-top: 14px;">
          <div class="v2-stat-label">活跃项目</div>
          <div class="v2-stat-value" style="color: var(--rs2-accent);">{{ stats.activeProjects }}</div>
        </div>
      </div>
      <div class="v2-panel" style="padding: 18px 16px;">
        <span class="v2-panel-tag warning">VULN</span>
        <div style="padding-top: 14px;">
          <div class="v2-stat-label">发现漏洞</div>
          <div class="v2-stat-value" style="color: var(--rs2-warning);">{{ stats.totalFindings }}</div>
        </div>
      </div>
      <div class="v2-panel alert-emphasis" style="padding: 18px 16px;">
        <span class="v2-panel-tag danger">ALERT</span>
        <div style="padding-top: 14px;">
          <div class="v2-stat-label">严重 / 高危</div>
          <div class="v2-stat-value" style="color: var(--rs2-danger);">{{ stats.criticalHigh }}</div>
        </div>
      </div>
      <div class="v2-panel" style="padding: 18px 16px;">
        <span class="v2-panel-tag success">FIX</span>
        <div style="padding-top: 14px;">
          <div class="v2-stat-label">修复率</div>
          <div class="v2-stat-value" style="color: var(--rs2-success);">{{ stats.fixRate }}<span style="font-size:18px;opacity:0.6;">%</span></div>
        </div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 320px; gap: 2px; margin-bottom: 2px;">
      <div class="v2-panel" style="min-height: 300px;">
        <span class="v2-panel-tag danger">RECENT FINDINGS</span>
        <div class="v2-panel-body">
          <table class="v2-data-table">
            <thead><tr><th>等级</th><th>漏洞</th><th>目标</th><th>项目</th><th>来源</th></tr></thead>
            <tbody>
              <tr v-for="f in recentFindings" :key="f.id" @click="goToFinding(f)">
                <td><span class="v2-sev" :class="f.severity">{{ sevLabel[f.severity] || f.severity }}</span></td>
                <td style="color: var(--rs2-text-primary); font-weight: 500; font-family: var(--rs2-sans);">{{ f.title }}</td>
                <td>{{ f.host || '-' }}</td>
                <td style="font-family: var(--rs2-sans);">{{ f.project_name || '' }}</td>
                <td>{{ f.found_by || '-' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="!recentFindings.length" style="text-align: center; padding: 40px; color: var(--rs2-text-muted); font-size: 12px;">暂无漏洞数据</div>
        </div>
      </div>

      <div class="v2-panel">
        <span class="v2-panel-tag">LIVE SCANS</span>
        <div class="v2-panel-body" style="padding: 32px 0 0 0;">
          <div v-for="s in activeScans" :key="s.id" style="padding: 10px 12px; border-bottom: 1px solid rgba(26,39,68,0.4); cursor: pointer; transition: background 0.1s;" @click="router.push(`/v2/projects/${s.project_id}/scanning`)" @mouseenter="$event.currentTarget.style.background='var(--rs2-accent-dim)'" @mouseleave="$event.currentTarget.style.background='transparent'">
            <div style="font-size: 12px; color: var(--rs2-text-primary); margin-bottom: 2px;">{{ s.task_name }}</div>
            <div style="display: flex; justify-content: space-between; font-family: var(--rs2-mono); font-size: 10px; color: var(--rs2-text-muted);">
              <span>{{ s.scan_strategy }}</span>
              <span style="color: var(--rs2-warning);">{{ s.progress || 0 }}%</span>
            </div>
            <div class="v2-progress-bar" style="margin-top: 6px;">
              <div class="v2-progress-fill" :style="{ width: (s.progress || 0) + '%', background: 'var(--rs2-warning)' }"></div>
            </div>
          </div>
          <div v-if="!activeScans.length" style="text-align: center; padding: 30px; color: var(--rs2-text-muted); font-size: 12px;">暂无运行中的扫描</div>
        </div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2px;">
      <div class="v2-panel">
        <span class="v2-panel-tag">PROJECTS</span>
        <div class="v2-panel-body">
          <table class="v2-data-table">
            <thead><tr><th>项目</th><th>客户</th><th>模式</th><th>资产</th><th>漏洞</th><th>状态</th></tr></thead>
            <tbody>
              <tr v-for="proj in recentProjects" :key="proj.id" @click="$router.push(`/v2/projects/${proj.id}`)">
                <td style="color: var(--rs2-text-primary); font-weight: 500; font-family: var(--rs2-sans);">{{ proj.name }}</td>
                <td style="font-family: var(--rs2-sans);">{{ proj.client_name || '—' }}</td>
                <td><span class="v2-sev" :class="proj.mode === 'combat' ? 'critical' : proj.mode === 'range' ? 'medium' : 'low'">{{ {combat:'实战',range:'靶场',research:'研究'}[proj.mode] }}</span></td>
                <td>{{ proj.asset_count }}</td>
                <td>{{ proj.finding_count }}</td>
                <td><span class="v2-status-dot" :class="proj.status === 'active' ? 'green' : 'amber'" style="margin-right:4px;"></span>{{ {active:'进行中',paused:'暂停',completed:'完成'}[proj.status] || proj.status }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="v2-panel">
        <span class="v2-panel-tag">SYS STATUS</span>
        <div class="v2-panel-body">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px;">
            <div class="v2-host-card">
              <div><div style="font-family:var(--rs2-mono);font-size:11px;color:var(--rs2-text-primary);">PostgreSQL</div><div style="font-family:var(--rs2-mono);font-size:9px;color:var(--rs2-text-muted);">{{ health.database === 'ok' ? '正常' : '异常' }}</div></div>
              <span class="v2-status-dot" :class="health.database === 'ok' ? 'green' : 'amber'"></span>
            </div>
            <div class="v2-host-card">
              <div><div style="font-family:var(--rs2-mono);font-size:11px;color:var(--rs2-text-primary);">Redis</div><div style="font-family:var(--rs2-mono);font-size:9px;color:var(--rs2-text-muted);">{{ health.redis === 'ok' ? '正常' : '异常' }}</div></div>
              <span class="v2-status-dot" :class="health.redis === 'ok' ? 'green' : 'amber'"></span>
            </div>
            <div class="v2-host-card">
              <div><div style="font-family:var(--rs2-mono);font-size:11px;color:var(--rs2-text-primary);">工具引擎</div><div style="font-family:var(--rs2-mono);font-size:9px;color:var(--rs2-text-muted);">{{ stats.pluginCount }} 个</div></div>
              <span class="v2-status-dot green"></span>
            </div>
            <div class="v2-host-card">
              <div><div style="font-family:var(--rs2-mono);font-size:11px;color:var(--rs2-text-primary);">扫描任务</div><div style="font-family:var(--rs2-mono);font-size:9px;color:var(--rs2-text-muted);">{{ activeScans.length }} 运行中</div></div>
              <span class="v2-status-dot" :class="activeScans.length ? 'amber' : 'green'"></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showQuickScan" title="快速扫描" width="560px">
      <el-form :model="scanForm" label-width="100px">
        <el-form-item label="选择项目" required>
          <el-select v-model="scanForm.project_id" placeholder="选择项目" style="width: 100%;">
            <el-option v-for="proj in recentProjects" :key="proj.id" :value="proj.id" :label="proj.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="扫描目标" required>
          <el-input v-model="scanForm.targetsText" type="textarea" :rows="4" placeholder="每行一个目标&#10;例: http://192.168.1.100:8080&#10;     10.0.0.0/24&#10;     example.com" />
        </el-form-item>
        <el-form-item label="扫描策略">
          <el-radio-group v-model="scanForm.strategy">
            <el-radio-button value="quick">快速</el-radio-button>
            <el-radio-button value="standard">标准</el-radio-button>
            <el-radio-button value="deep">深度</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showQuickScan = false">取消</el-button>
        <el-button type="primary" @click="startQuickScan" :loading="scanning">开始扫描</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../stores/api'

const router = useRouter()
const stats = ref({ activeProjects: 0, totalFindings: 0, criticalHigh: 0, fixRate: 0, pluginCount: 0 })
const recentProjects = ref([])
const activeScans = ref([])
const recentFindings = ref([])
const health = ref({ database: 'ok', redis: 'ok' })
const showQuickScan = ref(false)
const scanning = ref(false)
const scanForm = ref({ project_id: null, targetsText: '', strategy: 'standard' })
const lastSync = ref('JUST NOW')

const sevLabel = { critical: 'CRIT', high: 'HIGH', medium: 'MED', low: 'LOW', info: 'INFO' }

const goToFinding = (f) => {
  if (f.project_id) router.push(`/v2/projects/${f.project_id}/findings`)
}

const startQuickScan = async () => {
  if (!scanForm.value.project_id) { ElMessage.warning('请选择项目'); return }
  const targets = scanForm.value.targetsText.split('\n').map(s => s.trim()).filter(Boolean)
  if (!targets.length) { ElMessage.warning('请输入至少一个目标'); return }
  scanning.value = true
  try {
    await api.post(`/projects/${scanForm.value.project_id}/scans`, {
      task_name: `快速扫描 - ${new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`,
      scan_strategy: scanForm.value.strategy,
      targets,
    })
    showQuickScan.value = false
    ElMessage.success('扫描任务已创建')
    router.push(`/v2/projects/${scanForm.value.project_id}/scanning`)
  } catch (e) {
    const detail = e.response?.data?.detail
    ElMessage.error(detail?.message || detail || '创建失败')
  } finally { scanning.value = false }
}

onMounted(async () => {
  const tasks = []
  tasks.push(api.get('/dashboard/summary').then(res => {
    stats.value.activeProjects = res.active_projects
    stats.value.totalFindings = res.total_findings
    stats.value.criticalHigh = res.critical_high
    stats.value.fixRate = res.fix_rate
    recentProjects.value = res.recent_projects || []
    activeScans.value = res.active_scans || []
    recentFindings.value = res.recent_findings || []
  }).catch(() => {}))

  tasks.push(api.get('/health').then(r => { health.value = r }).catch(() => {}))
  tasks.push(api.get('/plugins').then(r => { stats.value.pluginCount = (r.items || []).length }).catch(() => {}))

  await Promise.all(tasks)
  lastSync.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})
</script>
