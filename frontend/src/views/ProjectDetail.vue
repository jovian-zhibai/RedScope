<template>
  <div v-if="project">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <div>
        <h2>{{ project.name }}</h2>
        <div style="color: var(--rs-text-secondary); font-size: 13px; margin-top: 4px;">
          {{ project.client_name }} ·
          <span class="severity-badge" :class="project.mode === 'combat' ? 'critical' : project.mode === 'range' ? 'medium' : 'low'">
            {{ {combat: '实战', range: '靶场', research: '研究'}[project.mode] }}
          </span>
          <template v-if="project.auth_end_date"> · 授权至 {{ project.auth_end_date }}</template>
        </div>
      </div>
      <div style="display: flex; gap: 8px;">
        <el-button size="small" @click="cloneProject" :loading="cloning">克隆项目</el-button>
        <el-button type="danger" plain @click="emergencyStop">🔴 紧急停止</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <div class="stat-card info"><div class="stat-label">资产总数</div><div class="stat-value">{{ project.asset_count }}</div></div>
      <div class="stat-card warning"><div class="stat-label">发现漏洞</div><div class="stat-value">{{ project.finding_count }}</div></div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="资产" name="assets">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="$router.push(`/projects/${project.id}/assets`)">管理资产 →</el-button>
          <el-upload :action="`/api/projects/${project.id}/import/csv-assets`" :headers="uploadHeaders" :on-success="onImportSuccess" :show-file-list="false" accept=".csv">
            <el-button size="small">导入CSV资产</el-button>
          </el-upload>
          <el-upload :action="`/api/projects/${project.id}/import/nessus`" :headers="uploadHeaders" :on-success="onImportSuccess" :show-file-list="false" accept=".nessus,.xml">
            <el-button size="small">导入Nessus报告</el-button>
          </el-upload>
        </div>
      </el-tab-pane>

      <el-tab-pane label="扫描" name="scanning">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="$router.push(`/projects/${project.id}/scanning`)">扫描任务 →</el-button>
          <el-button size="small" @click="showPipeline = true">运行流水线</el-button>
          <el-button size="small" @click="runVulnMatch" :loading="matching">被动漏洞匹配</el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="漏洞" name="findings">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="$router.push(`/projects/${project.id}/findings`)">漏洞列表 →</el-button>
          <el-button size="small" @click="runDedup">去重合并</el-button>
          <el-button size="small" @click="runScoreRisks">重算风险评分</el-button>
          <el-button size="small" @click="exportFindings">导出漏洞CSV</el-button>
          <el-button size="small" @click="exportArchive">导出项目归档</el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="报告" name="reports">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="generateReport" :loading="generating">生成渗透测试报告</el-button>
          <el-button size="small" @click="aiReportSummary" :loading="aiSummarizing">AI 生成总结</el-button>
        </div>
        <div v-if="aiSummary" class="card" style="padding: 16px; margin-bottom: 16px; border-left: 4px solid var(--rs-accent);">
          <h4 style="margin-bottom: 8px;">AI 报告总结</h4>
          <div style="white-space: pre-wrap; font-size: 13px;">{{ aiSummary }}</div>
        </div>
        <el-table :data="reports" style="width: 100%;">
          <el-table-column prop="title" label="报告名称" min-width="200" />
          <el-table-column prop="report_type" label="类型" width="100" />
          <el-table-column prop="format" label="格式" width="80" />
          <el-table-column prop="generated_at" label="生成时间" width="180"><template #default="{ row }">{{ row.generated_at || '生成中...' }}</template></el-table-column>
        </el-table>
        <el-empty v-if="!reports.length" description="暂无报告" />
      </el-tab-pane>

      <el-tab-pane label="作战管理" name="operations">
        <el-button type="primary" size="small" @click="$router.push(`/projects/${project.id}/operations`)">代理/凭据/主机/时间线/清理 →</el-button>
      </el-tab-pane>

      <el-tab-pane label="手工测试" name="testing">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="$router.push(`/projects/${project.id}/testing`)">测试清单/Payload/笔记/分工 →</el-button>
        </div>
        <div style="color: var(--rs-text-secondary); font-size: 13px;">
          包含：逻辑漏洞Checklist、Payload武器库、测试笔记、任务分工防撞车
        </div>
      </el-tab-pane>

      <el-tab-pane label="红蓝对抗" name="redblue">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="$router.push(`/projects/${project.id}/redblue`)">护网计分板 →</el-button>
        </div>
        <div style="color: var(--rs-text-secondary); font-size: 13px;">
          红蓝对抗演练计分、实时积分排名
        </div>
      </el-tab-pane>

      <el-tab-pane label="LLM安全测试" name="llmtest">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="$router.push(`/projects/${project.id}/llm-test`)">LLM OWASP Top 10 测试 →</el-button>
        </div>
        <div style="color: var(--rs-text-secondary); font-size: 13px;">
          自动化测试 LLM 应用：Prompt注入、数据泄露、越权、幻觉检测等
        </div>
      </el-tab-pane>

      <el-tab-pane label="ATT&CK" name="attck">
        <div style="margin-bottom: 12px;">
          <el-button size="small" @click="loadHeatmap">刷新热力图</el-button>
          <el-button size="small" @click="autoMapAttck">自动补全ATT&CK映射</el-button>
          <span v-if="heatmapData" style="margin-left: 12px; color: var(--rs-text-secondary);">覆盖 {{ heatmapData.total_techniques }} 个技术</span>
        </div>
        <div v-if="heatmapData" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
          <div v-for="(data, tactic) in heatmapData.heatmap" :key="tactic" class="card" style="padding: 12px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">{{ tactic }}</div>
            <div style="font-size: 20px; font-weight: bold;" :style="{ color: data.count > 0 ? 'var(--rs-danger)' : 'var(--rs-text-secondary)' }">{{ data.count }}</div>
            <div style="font-size: 11px; color: var(--rs-text-secondary);">{{ data.techniques.join(', ') }}</div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="边界" name="scope">
        <ScopeManager :project-id="project.id" :mode="project.mode" />
      </el-tab-pane>

      <el-tab-pane label="网络拓扑" name="topology">
        <NetworkTopology :project-id="project.id" />
      </el-tab-pane>
    </el-tabs>

    <!-- Pipeline Dialog -->
    <el-dialog v-model="showPipeline" title="运行扫描流水线" width="520px">
      <div v-if="pipelines.length" style="margin-bottom: 16px;">
        <div v-for="p in pipelines" :key="p.file" class="card" style="cursor: pointer; padding: 12px; margin-bottom: 8px;" @click="selectedPipeline = p.file">
          <div style="display: flex; justify-content: space-between;">
            <strong :style="{ color: selectedPipeline === p.file ? 'var(--rs-accent)' : '' }">{{ p.name }}</strong>
            <el-tag size="small">{{ p.node_count }} 步</el-tag>
          </div>
          <div style="font-size: 12px; color: var(--rs-text-secondary);">{{ p.description }}</div>
        </div>
      </div>
      <el-input v-model="pipelineTargets" type="textarea" :rows="4" placeholder="每行一个目标" />
      <template #footer>
        <el-button @click="showPipeline = false">取消</el-button>
        <el-button type="primary" @click="runPipeline" :loading="runningPipeline">执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import api from '../stores/api'
import ScopeManager from '../components/ScopeManager.vue'
import NetworkTopology from '../components/NetworkTopology.vue'

const route = useRoute()
const router = useRouter()
const pid = route.params.id
const project = ref(null)
const activeTab = ref('assets')
const reports = ref([])
const generating = ref(false)
const matching = ref(false)
const heatmapData = ref(null)
const aiSummarizing = ref(false)
const aiSummary = ref('')
const cloning = ref(false)

const showPipeline = ref(false)
const pipelines = ref([])
const selectedPipeline = ref('')
const pipelineTargets = ref('')
const runningPipeline = ref(false)

const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }

onMounted(async () => {
  project.value = await api.get(`/projects/${pid}`)
  try { const res = await api.get(`/projects/${pid}/reports`); reports.value = res.items || [] } catch(e) {}
})

const emergencyStop = async () => {
  await ElMessageBox.confirm('确认紧急停止所有扫描任务？', '紧急停止', { type: 'warning' })
  await api.post(`/projects/${pid}/emergency-stop`)
  ElMessage.success('所有任务已停止')
}

const onImportSuccess = (res) => {
  ElMessage.success(res.message || `导入成功: ${res.imported} 条`)
  api.get(`/projects/${pid}`).then(r => project.value = r)
}

const runVulnMatch = async () => {
  matching.value = true
  try {
    const res = await api.post(`/projects/${pid}/match-vulns`)
    ElMessage.success(`被动匹配完成，发现 ${res.matched} 个潜在漏洞`)
  } finally { matching.value = false }
}

const runDedup = async () => {
  const res = await api.post(`/projects/${pid}/dedup`)
  ElMessage.success(`去重完成，合并 ${res.duplicates_merged} 个重复项`)
}

const runScoreRisks = async () => {
  const res = await api.post(`/projects/${pid}/score-risks`)
  ElMessage.success(res.message)
}

const exportFindings = () => { window.open(`/api/projects/${pid}/export/findings-csv`, '_blank') }
const exportArchive = async () => {
  const res = await api.get(`/projects/${pid}/export/archive`)
  const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = `project_${pid}_archive.json`; a.click()
}

const generateReport = async () => {
  generating.value = true
  try {
    const res = await api.post(`/projects/${pid}/reports/generate`, { title: `${project.value.name} - 渗透测试报告` })
    ElMessage.success('报告生成任务已提交')
    const r = await api.get(`/projects/${pid}/reports`); reports.value = r.items || []
  } finally { generating.value = false }
}

const loadHeatmap = async () => {
  heatmapData.value = await api.get(`/projects/${pid}/attck-heatmap`)
}

const autoMapAttck = async () => {
  const res = await api.post(`/projects/${pid}/auto-attck`)
  ElMessage.success(`自动映射完成: ${res.auto_mapped}/${res.total_unmapped} 条`)
  await loadHeatmap()
}

const loadPipelines = async () => {
  try { const res = await api.get('/pipelines'); pipelines.value = res.items || [] } catch(e) {}
}

const runPipeline = async () => {
  runningPipeline.value = true
  try {
    const targets = pipelineTargets.value.split('\n').filter(Boolean)
    const res = await api.post(`/projects/${pid}/run-pipeline`, { pipeline_name: selectedPipeline.value, targets })
    ElMessage.success('流水线执行完成')
    showPipeline.value = false
  } catch(e) {
    ElMessage.error(e.response?.data?.detail?.message || '执行失败')
  } finally { runningPipeline.value = false }
}

// Load pipelines when scanning tab shown
const onTabChange = () => { if (activeTab.value === 'scanning' && !pipelines.value.length) loadPipelines() }

const aiReportSummary = async () => {
  aiSummarizing.value = true
  try {
    const res = await api.post(`/projects/${pid}/ai-report-summary`)
    aiSummary.value = res.summary
  } catch (e) { ElMessage.error('AI 总结生成失败，请确认已配置 LLM API Key') }
  finally { aiSummarizing.value = false }
}

const cloneProject = async () => {
  cloning.value = true
  try {
    const res = await api.post(`/auth/projects/${pid}/clone`)
    ElMessage.success(`项目已克隆: ${res.name}`)
    router.push(`/projects/${res.id}`)
  } catch (e) { ElMessage.error('克隆失败') }
  finally { cloning.value = false }
}
</script>
