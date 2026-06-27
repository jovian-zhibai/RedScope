<template>
  <div v-if="project">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
      <div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <el-button text size="small" @click="$router.push(p('/projects'))" style="color: var(--rs-text-secondary);">← 项目列表</el-button>
          <h2 style="margin: 0;">{{ project.name }}</h2>
        </div>
        <div style="color: var(--rs-text-secondary); font-size: 13px; margin-top: 4px; margin-left: 80px;">
          {{ project.client_name }} ·
          <span class="severity-badge" :class="project.mode === 'combat' ? 'critical' : project.mode === 'range' ? 'medium' : 'low'">
            {{ {combat: '实战', range: '靶场', research: '研究'}[project.mode] }}
          </span>
          <template v-if="project.auth_end_date"> · 授权至 {{ project.auth_end_date }}</template>
        </div>
      </div>
      <div style="display: flex; gap: 8px;">
        <el-button size="small" @click="cloneProject" :loading="cloning">克隆</el-button>
        <el-button type="danger" plain size="small" @click="emergencyStop">紧急停止</el-button>
      </div>
    </div>

    <!-- Authorization Expiry Warning -->
    <div v-if="authExpired" style="padding: 12px 16px; margin-bottom: 16px; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; display: flex; align-items: center; gap: 12px;">
      <el-icon :size="20" style="color: var(--rs-danger);"><WarningFilled /></el-icon>
      <div>
        <div style="font-weight: 600; color: var(--rs-danger); font-size: 13px;">授权已过期</div>
        <div style="font-size: 12px; color: var(--rs-text-secondary);">项目授权截止日期为 {{ project.auth_end_date }}，请确认授权续期后再继续操作。</div>
      </div>
    </div>
    <div v-else-if="authExpiringSoon" style="padding: 12px 16px; margin-bottom: 16px; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); border-radius: 8px; display: flex; align-items: center; gap: 12px;">
      <el-icon :size="20" style="color: var(--rs-warning);"><Warning /></el-icon>
      <div>
        <div style="font-weight: 600; color: var(--rs-warning); font-size: 13px;">授权即将到期</div>
        <div style="font-size: 12px; color: var(--rs-text-secondary);">项目授权将于 {{ project.auth_end_date }} 到期，请及时联系客户确认续期。</div>
      </div>
    </div>

    <!-- Workflow Guide -->
    <div v-if="project.asset_count === 0" class="card" style="padding: 20px; margin-bottom: 16px; border-left: 4px solid var(--rs-accent);">
      <h4 style="margin-bottom: 12px;">快速开始</h4>
      <div style="font-size: 13px; color: var(--rs-text-secondary); margin-bottom: 16px;">添加扫描目标，一键开始扫描。</div>
      <el-input v-model="quickTargets" type="textarea" :rows="3" placeholder="每行一个目标（IP/域名/URL/CIDR）&#10;例:&#10;192.168.1.0/24&#10;http://testphp.vulnweb.com" style="margin-bottom: 12px;" />
      <div style="display: flex; gap: 8px;">
        <el-button type="primary" @click="quickStartScan" :loading="quickScanning" :disabled="!quickTargets.trim()">添加资产并开始扫描</el-button>
        <el-upload :action="`/api/v1/projects/${project.id}/import/csv-assets`" :headers="uploadHeaders" :on-success="onImportSuccess" :show-file-list="false" accept=".csv">
          <el-button>导入 CSV</el-button>
        </el-upload>
      </div>
    </div>

    <div class="stat-grid">
      <div class="stat-card info"><div class="stat-label">资产总数</div><div class="stat-value">{{ project.asset_count }}</div></div>
      <div class="stat-card warning"><div class="stat-label">发现漏洞</div><div class="stat-value">{{ project.finding_count }}</div></div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="资产" name="assets">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="$router.push(p(`/projects/${project.id}/assets`))">管理资产 →</el-button>
          <el-upload :action="`/api/v1/projects/${project.id}/import/csv-assets`" :headers="uploadHeaders" :on-success="onImportSuccess" :show-file-list="false" accept=".csv">
            <el-button size="small">导入CSV资产</el-button>
          </el-upload>
          <el-upload :action="`/api/v1/projects/${project.id}/import/nessus`" :headers="uploadHeaders" :on-success="onImportSuccess" :show-file-list="false" accept=".nessus,.xml">
            <el-button size="small">导入Nessus报告</el-button>
          </el-upload>
        </div>
      </el-tab-pane>

      <el-tab-pane label="扫描" name="scanning">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="$router.push(p(`/projects/${project.id}/scanning`))">扫描任务 →</el-button>
          <el-button size="small" @click="showPipeline = true">运行流水线</el-button>
          <el-button size="small" @click="runVulnMatch" :loading="matching">被动漏洞匹配</el-button>
          <el-button size="small" @click="runOpsecCheck" :loading="opsecChecking">OPSEC 预检</el-button>
        </div>
        <div v-if="opsecWarnings.length" style="margin-bottom: 12px;">
          <div v-for="(w, i) in opsecWarnings" :key="i" style="padding: 8px 12px; margin-bottom: 4px; border-radius: 6px; font-size: 13px;" :style="{ background: w.level === 'danger' ? 'rgba(248,81,73,0.1)' : 'rgba(210,153,34,0.1)', borderLeft: w.level === 'danger' ? '3px solid var(--rs-danger)' : '3px solid var(--rs-warning)' }">
            <strong>{{ w.category }}</strong>: {{ w.message }}<br/><span style="color: var(--rs-text-secondary);">{{ w.suggestion }}</span>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="漏洞" name="findings">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="$router.push(p(`/projects/${project.id}/findings`))">漏洞列表 →</el-button>
          <el-button size="small" @click="runDedup">去重合并</el-button>
          <el-button size="small" @click="runScoreRisks">重算风险评分</el-button>
          <el-button size="small" @click="exportFindings">导出漏洞CSV</el-button>
          <el-button size="small" @click="exportArchive">导出项目归档</el-button>
        </div>

        <!-- Risk Acceptances -->
        <div v-if="riskAcceptances.length" style="margin-top: 12px;">
          <h4 style="margin-bottom: 8px;">客户风险接受记录 ({{ riskAcceptances.length }})</h4>
          <el-table :data="riskAcceptances" size="small" style="width: 100%;">
            <el-table-column prop="finding_id" label="漏洞ID" width="80" />
            <el-table-column prop="client_name" label="客户" width="120" />
            <el-table-column prop="accepted_by" label="接受人" width="120" />
            <el-table-column prop="reason" label="原因" min-width="200" />
            <el-table-column prop="accepted_at" label="时间" width="160"><template #default="{ row }">{{ row.accepted_at?.replace('T', ' ').slice(0, 19) }}</template></el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="报告" name="reports">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="generateReport" :loading="generating">生成渗透测试报告</el-button>
          <el-button size="small" @click="aiReportSummary" :loading="aiSummarizing">AI 生成总结</el-button>
          <el-button size="small" type="warning" @click="aiRepairRoadmap" :loading="roadmapping">AI 修复路线图</el-button>
          <el-button size="small" @click="aiBuildAttackChain" :loading="buildingChain">AI 攻击链推导</el-button>
        </div>
        <div v-if="aiSummary" class="card" style="padding: 16px; margin-bottom: 16px; border-left: 4px solid var(--rs-accent);">
          <h4 style="margin-bottom: 8px;">AI 报告总结</h4>
          <div style="white-space: pre-wrap; font-size: 13px;">{{ aiSummary }}</div>
        </div>
        <div v-if="repairRoadmap" class="card" style="padding: 16px; margin-bottom: 16px; border-left: 4px solid var(--rs-warning);">
          <h4 style="margin-bottom: 8px;">修复路线图</h4>
          <div style="white-space: pre-wrap; font-size: 13px;">{{ repairRoadmap }}</div>
        </div>
        <div v-if="attackChainText" class="card" style="padding: 16px; margin-bottom: 16px; border-left: 4px solid var(--rs-danger);">
          <h4 style="margin-bottom: 8px;">攻击链推导</h4>
          <div style="white-space: pre-wrap; font-size: 13px;">{{ attackChainText }}</div>
        </div>
        <el-table :data="reports" style="width: 100%;">
          <el-table-column prop="title" label="报告名称" min-width="200" />
          <el-table-column prop="report_type" label="类型" width="100" />
          <el-table-column prop="format" label="格式" width="80" />
          <el-table-column prop="generated_at" label="生成时间" width="180"><template #default="{ row }">{{ row.generated_at?.replace('T', ' ').slice(0, 19) || '生成中...' }}</template></el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <template v-if="row.has_file">
                <el-button size="small" @click.stop="previewReport(row.id)">预览</el-button>
                <el-button size="small" type="primary" @click.stop="downloadReport(row.id)">下载</el-button>
              </template>
              <el-tag v-else-if="!row.generated_at" size="small" type="warning">生成中</el-tag>
              <el-tag v-else size="small" type="info">文件不可用</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!reports.length" description="暂无报告" />

        <!-- Report Preview Dialog -->
        <el-dialog v-model="showReportPreview" title="报告预览" width="800px" top="5vh">
          <div v-if="reportPreview" style="max-height: 70vh; overflow-y: auto;">
            <div style="text-align: center; margin-bottom: 24px;">
              <h2 style="font-size: 22px;">渗透测试报告</h2>
              <div style="color: var(--rs-text-secondary); margin-top: 8px;">{{ reportPreview.project_name }}</div>
              <div v-if="reportPreview.client_name" style="color: var(--rs-text-secondary);">客户: {{ reportPreview.client_name }}</div>
              <div style="color: var(--rs-text-secondary); font-size: 12px; margin-top: 4px;">{{ reportPreview.generated_at?.replace('T', ' ').slice(0, 19) }}</div>
            </div>

            <h3 style="margin: 16px 0 12px; border-bottom: 1px solid var(--rs-border); padding-bottom: 8px;">一、测试概述</h3>
            <p style="font-size: 13px; line-height: 1.8;">
              本次渗透测试共发现 <strong>{{ reportPreview.summary.total }}</strong> 个安全漏洞，
              其中严重 <span style="color: var(--rs-danger);">{{ reportPreview.summary.critical }}</span> 个，
              高危 <span style="color: var(--rs-warning);">{{ reportPreview.summary.high }}</span> 个，
              中危 {{ reportPreview.summary.medium }} 个，
              低危 {{ reportPreview.summary.low }} 个。
              测试资产总数: {{ reportPreview.summary.asset_count }} 个。
            </p>

            <h3 style="margin: 20px 0 12px; border-bottom: 1px solid var(--rs-border); padding-bottom: 8px;">二、漏洞详情</h3>
            <div v-for="(f, i) in reportPreview.findings" :key="i" style="margin-bottom: 16px; padding: 12px; background: var(--rs-bg-secondary); border-radius: 8px; border-left: 3px solid" :style="{ borderLeftColor: {critical:'var(--rs-danger)',high:'var(--rs-warning)',medium:'var(--rs-accent)',low:'var(--rs-success)'}[f.severity] || 'var(--rs-border)' }">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong style="font-size: 14px;">{{ i + 1 }}. {{ f.title }}</strong>
                <span class="severity-badge" :class="f.severity">{{ f.severity }}</span>
              </div>
              <div v-if="f.description" style="font-size: 13px; color: var(--rs-text-secondary); margin-bottom: 6px;">{{ f.description }}</div>
              <div v-if="f.detail" style="font-size: 12px; margin-bottom: 6px;"><strong>复现步骤:</strong> <span style="color: var(--rs-text-secondary);">{{ f.detail.slice(0, 300) }}</span></div>
              <div v-if="f.solution" style="font-size: 12px;"><strong>修复建议:</strong> <span style="color: var(--rs-text-secondary);">{{ f.solution.slice(0, 300) }}</span></div>
            </div>
            <div v-if="!reportPreview.findings.length" style="color: var(--rs-text-secondary); text-align: center; padding: 20px;">暂无漏洞数据</div>
          </div>
          <template #footer>
            <el-button @click="showReportPreview = false">关闭</el-button>
            <el-button type="primary" @click="downloadReport(previewReportId); showReportPreview = false">下载 Word</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <el-tab-pane label="工作Session" name="sessions">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="startSession" :loading="startingSession">开始新 Session</el-button>
          <el-button v-if="activeSessionId" type="warning" size="small" @click="endSession" :loading="endingSession">结束当前 Session</el-button>
          <span v-if="activeSessionId" style="color: var(--rs-success); font-size: 13px; line-height: 32px;">● 工作中</span>
        </div>
        <el-table :data="sessions" style="width: 100%;">
          <el-table-column prop="title" label="标题" min-width="200" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '进行中' : '已结束' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="scans_run" label="扫描" width="60" />
          <el-table-column prop="findings_added" label="漏洞" width="60" />
          <el-table-column prop="screenshots_count" label="截图" width="60" />
          <el-table-column prop="started_at" label="开始" width="140"><template #default="{ row }">{{ row.started_at?.replace('T', ' ').slice(0, 16) }}</template></el-table-column>
          <el-table-column prop="summary" label="摘要" min-width="250">
            <template #default="{ row }"><span style="font-size: 12px; color: var(--rs-text-secondary);">{{ row.summary?.slice(0, 100) }}</span></template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!sessions.length" description="暂无工作记录" />

        <!-- Screenshot upload -->
        <div v-if="activeSessionId" style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px;">上传截图</h4>
          <el-upload
            :action="`/api/v1/projects/${project.id}/screenshots?session_id=${activeSessionId}`"
            :headers="uploadHeaders"
            :on-success="onScreenshotUploaded"
            :show-file-list="false"
            accept=".png,.jpg,.jpeg,.gif,.bmp,.webp"
            drag
            style="width: 100%;"
          >
            <div style="padding: 20px; text-align: center; color: var(--rs-text-secondary);">
              拖拽截图到此处 或 <em>点击上传</em>
            </div>
          </el-upload>
        </div>

        <!-- Screenshots list -->
        <div v-if="screenshots.length" style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px;">截图 ({{ screenshots.length }})</h4>
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            <div v-for="s in screenshots" :key="s.id" class="card" style="width: 150px; padding: 8px; cursor: pointer;" @click="previewScreenshot(s)">
              <img :src="s.view_url" style="width: 100%; border-radius: 4px;" />
              <div style="font-size: 11px; color: var(--rs-text-secondary); margin-top: 4px;">{{ s.caption || s.filename }}</div>
            </div>
          </div>
        </div>

        <!-- Recordings -->
        <div style="margin-top: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <h4>终端录制 / Playbook</h4>
            <el-button size="small" @click="showRecordForm = true"><el-icon><Plus /></el-icon> 保存录制</el-button>
          </div>
          <el-table :data="recordings" style="width: 100%;" size="small">
            <el-table-column prop="title" label="标题" min-width="150" />
            <el-table-column prop="commands_count" label="命令数" width="80" />
            <el-table-column prop="duration_seconds" label="时长(秒)" width="80" />
            <el-table-column prop="is_playbook" label="Playbook" width="80">
              <template #default="{ row }">{{ row.is_playbook ? '✅' : '' }}</template>
            </el-table-column>
            <el-table-column prop="recorded_at" label="时间" width="140">
              <template #default="{ row }">{{ row.recorded_at?.replace('T', ' ').slice(0, 16) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!recordings.length" description="暂无录制" :image-size="40" />
        </div>

        <!-- Save Recording Dialog -->
        <el-dialog v-model="showRecordForm" title="保存终端录制" width="480px">
          <el-form :model="recordForm" label-width="100px">
            <el-form-item label="标题"><el-input v-model="recordForm.title" placeholder="如: 横向移动到 DB 服务器" /></el-form-item>
            <el-form-item label="命令列表"><el-input v-model="recordForm.commands_text" type="textarea" :rows="5" placeholder="每行一条命令" /></el-form-item>
            <el-form-item label="时长(秒)"><el-input-number v-model="recordForm.duration_seconds" :min="0" /></el-form-item>
            <el-form-item label="保存为 Playbook"><el-switch v-model="recordForm.is_playbook" /></el-form-item>
            <el-form-item v-if="recordForm.is_playbook" label="Playbook 名称"><el-input v-model="recordForm.playbook_name" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showRecordForm = false">取消</el-button>
            <el-button type="primary" @click="saveRecording">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <el-tab-pane label="作战 & 测试" name="operations">
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;">
          <div class="card onboard-step" @click="$router.push(p(`/projects/${project.id}/operations`))">
            <el-icon :size="28" style="margin-bottom: 8px; color: var(--rs-accent);"><Aim /></el-icon>
            <div style="font-weight: bold;">作战管理</div>
            <div style="font-size: 12px; color: var(--rs-text-secondary);">代理/凭据/主机/时间线</div>
          </div>
          <div class="card onboard-step" @click="$router.push(p(`/projects/${project.id}/testing`))">
            <el-icon :size="28" style="margin-bottom: 8px; color: var(--rs-warning);"><EditPen /></el-icon>
            <div style="font-weight: bold;">手工测试</div>
            <div style="font-size: 12px; color: var(--rs-text-secondary);">Checklist/Payload/笔记</div>
          </div>
          <div class="card onboard-step" @click="$router.push(p(`/projects/${project.id}/redblue`))">
            <el-icon :size="28" style="margin-bottom: 8px; color: var(--rs-danger);"><TrophyBase /></el-icon>
            <div style="font-weight: bold;">红蓝对抗</div>
            <div style="font-size: 12px; color: var(--rs-text-secondary);">护网计分板</div>
          </div>
          <div class="card onboard-step" @click="$router.push(p(`/projects/${project.id}/llm-test`))">
            <el-icon :size="28" style="margin-bottom: 8px; color: var(--rs-purple);"><MagicStick /></el-icon>
            <div style="font-weight: bold;">LLM 安全测试</div>
            <div style="font-size: 12px; color: var(--rs-text-secondary);">OWASP Top 10 自动化</div>
          </div>
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import api from '../stores/api'
import ScopeManager from '../components/ScopeManager.vue'
import NetworkTopology from '../components/NetworkTopology.vue'
import { useVersionPrefix } from '../composables/useVersionPrefix'

const route = useRoute()
const router = useRouter()
const { p } = useVersionPrefix()
const pid = route.params.id
const project = ref(null)

const authExpired = computed(() => {
  if (!project.value?.auth_end_date) return false
  return new Date(project.value.auth_end_date) < new Date()
})
const authExpiringSoon = computed(() => {
  if (!project.value?.auth_end_date || authExpired.value) return false
  const diff = new Date(project.value.auth_end_date) - new Date()
  return diff < 7 * 24 * 60 * 60 * 1000
})
const activeTab = ref('assets')
const workflowStep = ref(0)
const reports = ref([])
const generating = ref(false)
const matching = ref(false)
const heatmapData = ref(null)
const aiSummarizing = ref(false)
const aiSummary = ref('')
const cloning = ref(false)
const roadmapping = ref(false)
const repairRoadmap = ref('')
const buildingChain = ref(false)
const attackChainText = ref('')
const sessions = ref([])
const activeSessionId = ref(null)
const startingSession = ref(false)
const endingSession = ref(false)
const screenshots = ref([])
const recordings = ref([])

const showPipeline = ref(false)
const pipelines = ref([])
const selectedPipeline = ref('')
const pipelineTargets = ref('')
const runningPipeline = ref(false)
const riskAcceptances = ref([])
const opsecChecking = ref(false)
const opsecWarnings = ref([])
const showRecordForm = ref(false)
const recordForm = ref({ title: '', commands_text: '', duration_seconds: 0, is_playbook: false, playbook_name: '' })

const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }
const quickTargets = ref('')
const quickScanning = ref(false)

const quickStartScan = async () => {
  const targets = quickTargets.value.split('\n').map(s => s.trim()).filter(Boolean)
  if (!targets.length) return
  quickScanning.value = true
  try {
    await api.post(`/projects/${pid}/scans`, {
      task_name: `初始扫描 - ${new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`,
      scan_strategy: 'standard',
      targets,
    })
    ElMessage.success('扫描任务已创建')
    router.push(p(`/projects/${pid}/scanning`))
  } catch (e) {
    const detail = e.response?.data?.detail
    ElMessage.error(detail?.message || '创建扫描失败')
  } finally { quickScanning.value = false }
}

onMounted(async () => {
  try {
    project.value = await api.get(`/projects/${pid}`)
  } catch (e) {
    ElMessage.error('项目加载失败，可能已被删除')
    return
  }
  const loads = [
    api.get(`/projects/${pid}/reports`).then(r => { reports.value = r.items || [] }).catch(() => {}),
    api.get(`/projects/${pid}/sessions`).then(r => {
      sessions.value = r.items || []
      const active = sessions.value.find(s => s.status === 'active')
      if (active) { activeSessionId.value = active.id; sessionStorage.setItem(`rs_active_session_${pid}`, active.id) }
    }).catch(() => {}),
    api.get(`/projects/${pid}/screenshots`).then(r => { screenshots.value = r.items || [] }).catch(() => {}),
    api.get(`/projects/${pid}/recordings`).then(r => { recordings.value = r.items || [] }).catch(() => {}),
    api.get(`/projects/${pid}/risk-acceptances`).then(r => { riskAcceptances.value = r.items || [] }).catch(() => {}),
  ]
  await Promise.all(loads)
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

const exportFindings = () => { window.open(`/api/v1/projects/${pid}/export/findings-csv?token=${localStorage.getItem('token')}`, '_blank') }
const downloadReport = (reportId) => { window.open(`/api/v1/projects/${pid}/reports/${reportId}/download?token=${localStorage.getItem('token')}`, '_blank') }

const showReportPreview = ref(false)
const reportPreview = ref(null)
const previewReportId = ref(null)
const previewReport = async (reportId) => {
  previewReportId.value = reportId
  try {
    reportPreview.value = await api.get(`/projects/${pid}/reports/${reportId}/preview`)
    showReportPreview.value = true
  } catch (e) { ElMessage.error('预览加载失败') }
}
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

const runOpsecCheck = async () => {
  opsecChecking.value = true
  try {
    const res = await api.post(`/projects/${pid}/opsec-check`, { engine_name: 'nuclei', concurrency: 50, target_count: 10 })
    opsecWarnings.value = res.warnings || []
    if (!opsecWarnings.value.length) ElMessage.success('OPSEC 检查通过，无告警')
  } catch (e) { ElMessage.error('OPSEC 检查失败') }
  finally { opsecChecking.value = false }
}

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
    router.push(p(`/projects/${res.id}`))
  } catch (e) { ElMessage.error('克隆失败') }
  finally { cloning.value = false }
}

const saveAsTemplate = async () => {
  try {
    const res = await api.post(`/templates/from-project/${pid}`, { name: `${project.value.name} 模板` })
    ElMessage.success(`已保存为模板: ${res.name}`)
  } catch (e) { ElMessage.error('保存失败') }
}

const aiRepairRoadmap = async () => {
  roadmapping.value = true
  try {
    const res = await api.post(`/projects/${pid}/ai/repair-roadmap`)
    repairRoadmap.value = res.roadmap
  } catch (e) { ElMessage.error('生成失败') }
  finally { roadmapping.value = false }
}

const aiBuildAttackChain = async () => {
  buildingChain.value = true
  try {
    const res = await api.post(`/projects/${pid}/ai/build-attack-chain`)
    attackChainText.value = res.attack_path
    ElMessage.success('攻击链已生成并保存')
  } catch (e) { ElMessage.error('推导失败') }
  finally { buildingChain.value = false }
}

const startSession = async () => {
  startingSession.value = true
  try {
    const res = await api.post(`/projects/${pid}/sessions/start`, { title: '' })
    activeSessionId.value = res.id
    sessionStorage.setItem(`rs_active_session_${pid}`, res.id)
    ElMessage.success('工作 Session 已开始')
    const sr = await api.get(`/projects/${pid}/sessions`); sessions.value = sr.items || []
  } catch (e) { ElMessage.error(e.response?.data?.detail || '启动失败') }
  finally { startingSession.value = false }
}

const endSession = async () => {
  endingSession.value = true
  try {
    const res = await api.post(`/projects/${pid}/sessions/${activeSessionId.value}/end`)
    activeSessionId.value = null
    sessionStorage.removeItem(`rs_active_session_${pid}`)
    ElMessage.success('Session 已结束')
    const sr = await api.get(`/projects/${pid}/sessions`); sessions.value = sr.items || []
  } catch (e) { ElMessage.error('结束失败') }
  finally { endingSession.value = false }
}

const onScreenshotUploaded = async (res) => {
  ElMessage.success('截图已上传')
  try { const r = await api.get(`/projects/${pid}/screenshots`); screenshots.value = r.items || [] } catch {}
}

const previewScreenshot = (s) => {
  window.open(s.view_url, '_blank')
}

const saveRecording = async () => {
  if (!recordForm.value.title) { ElMessage.warning('请输入标题'); return }
  try {
    const commands = recordForm.value.commands_text.split('\n').filter(Boolean).map(c => ({ command: c, timestamp: new Date().toISOString() }))
    await api.post(`/projects/${pid}/recordings`, {
      session_id: activeSessionId.value,
      title: recordForm.value.title,
      commands,
      duration_seconds: recordForm.value.duration_seconds,
      is_playbook: recordForm.value.is_playbook,
      playbook_name: recordForm.value.playbook_name,
    })
    showRecordForm.value = false
    recordForm.value = { title: '', commands_text: '', duration_seconds: 0, is_playbook: false, playbook_name: '' }
    ElMessage.success('录制已保存')
    const r = await api.get(`/projects/${pid}/recordings`); recordings.value = r.items || []
  } catch (e) { ElMessage.error('保存失败') }
}
</script>
