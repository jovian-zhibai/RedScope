<template>
  <div>
    <!-- Quick Actions -->
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px;">
      <div class="card onboard-step" @click="quickCreate">
        <el-icon :size="24" style="margin-bottom: 6px; color: var(--rs-accent);"><FolderAdd /></el-icon>
        <div style="font-weight: 600; font-size: 13px;">新建项目</div>
      </div>
      <div class="card onboard-step" @click="showQuickScan = true">
        <el-icon :size="24" style="margin-bottom: 6px; color: var(--rs-warning);"><VideoPlay /></el-icon>
        <div style="font-weight: 600; font-size: 13px;">快速扫描</div>
      </div>
      <div class="card onboard-step" @click="$router.push('/ai')">
        <el-icon :size="24" style="margin-bottom: 6px; color: var(--rs-purple);"><MagicStick /></el-icon>
        <div style="font-weight: 600; font-size: 13px;">AI 助手</div>
      </div>
      <div class="card onboard-step" @click="$router.push('/vulns')">
        <el-icon :size="24" style="margin-bottom: 6px; color: var(--rs-danger);"><Warning /></el-icon>
        <div style="font-weight: 600; font-size: 13px;">漏洞管理</div>
      </div>
    </div>

    <!-- Stats -->
    <div class="stat-grid">
      <div class="stat-card info"><div class="stat-label">活跃项目</div><div class="stat-value">{{ stats.activeProjects }}</div></div>
      <div class="stat-card warning"><div class="stat-label">发现漏洞</div><div class="stat-value">{{ stats.totalFindings }}</div></div>
      <div class="stat-card critical"><div class="stat-label">严重/高危</div><div class="stat-value">{{ stats.criticalHigh }}</div></div>
      <div class="stat-card success"><div class="stat-label">修复率</div><div class="stat-value">{{ stats.fixRate }}%</div></div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
      <!-- Running Scans -->
      <div class="card">
        <h3 style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
          <span>运行中的扫描</span>
          <el-button size="small" text @click="$router.push('/scans')">查看全部</el-button>
        </h3>
        <div v-for="s in activeScans" :key="s.id" style="padding: 10px 0; border-bottom: 1px solid var(--rs-border);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-size: 13px;">{{ s.task_name }}</div>
              <div style="font-size: 11px; color: var(--rs-text-secondary);">{{ s.scan_strategy }}</div>
            </div>
            <el-progress :percentage="s.progress" :stroke-width="6" style="width: 80px;" />
          </div>
        </div>
        <div v-if="!activeScans.length" style="text-align: center; padding: 20px; color: var(--rs-text-secondary); font-size: 13px;">
          暂无运行中的扫描
        </div>
      </div>

      <!-- Recent Projects -->
      <div class="card">
        <h3 style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
          <span>项目</span>
          <el-button size="small" text @click="$router.push('/projects')">管理</el-button>
        </h3>
        <div v-for="p in recentProjects" :key="p.id"
          style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--rs-border); cursor: pointer;"
          @click="$router.push(`/projects/${p.id}`)">
          <div>
            <div style="font-size: 13px;">{{ p.name }}</div>
            <div style="font-size: 11px; color: var(--rs-text-secondary);">{{ p.client_name || '' }} · 资产 {{ p.asset_count }} · 漏洞 {{ p.finding_count }}</div>
          </div>
          <span class="severity-badge" :class="p.mode === 'combat' ? 'critical' : p.mode === 'range' ? 'medium' : 'low'">
            {{ {combat: '实战', range: '靶场', research: '研究'}[p.mode] }}
          </span>
        </div>
        <el-empty v-if="!recentProjects.length" description="暂无项目" :image-size="40" />
      </div>
    </div>

    <!-- System Status -->
    <div class="card" style="margin-top: 16px;">
      <h3 style="margin-bottom: 12px;">系统状态</h3>
      <div style="display: flex; gap: 24px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span :style="{ color: health.database === 'ok' ? 'var(--rs-success)' : 'var(--rs-danger)' }">●</span>
          数据库 {{ health.database === 'ok' ? '正常' : '异常' }}
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span :style="{ color: health.redis === 'ok' ? 'var(--rs-success)' : 'var(--rs-danger)' }">●</span>
          Redis {{ health.redis === 'ok' ? '正常' : '异常' }}
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="color: var(--rs-info);">●</span>
          工具 {{ stats.pluginCount }} 个
        </div>
      </div>
    </div>

    <!-- Quick Scan Dialog -->
    <el-dialog v-model="showQuickScan" title="快速扫描" width="560px">
      <el-form :model="scanForm" label-width="100px">
        <el-form-item label="选择项目" required>
          <el-select v-model="scanForm.project_id" placeholder="选择项目" style="width: 100%;">
            <el-option v-for="p in recentProjects" :key="p.id" :value="p.id" :label="p.name" />
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
import api from '../stores/api'

const router = useRouter()

const stats = ref({ activeProjects: 0, totalFindings: 0, criticalHigh: 0, fixRate: 0, pluginCount: 0 })
const recentProjects = ref([])
const activeScans = ref([])
const health = ref({ database: 'ok', redis: 'ok' })

const quickCreate = () => { router.push('/projects?action=create') }

const showQuickScan = ref(false)
const scanning = ref(false)
const scanForm = ref({ project_id: null, targetsText: '', strategy: 'standard' })

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
    router.push(`/projects/${scanForm.value.project_id}/scanning`)
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
  }).catch(() => {}))

  tasks.push(api.get('/health').then(r => { health.value = r }).catch(() => {}))
  tasks.push(api.get('/plugins').then(r => { stats.value.pluginCount = (r.items || []).length }).catch(() => {}))

  await Promise.all(tasks)
})
</script>
