<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>漏洞列表</h2>
      <div style="display: flex; gap: 8px;">
        <el-button v-if="selectedIds.length" size="small" @click="batchMarkFixed">批量标记已修复 ({{ selectedIds.length }})</el-button>
        <el-button v-if="selectedIds.length" size="small" @click="batchMarkFP">批量标记误报 ({{ selectedIds.length }})</el-button>
        <el-button type="primary" size="small" @click="showAdd = true"><el-icon><Plus /></el-icon> 手动录入</el-button>
      </div>
    </div>

    <div class="stat-grid" style="margin-bottom: 16px;">
      <div class="stat-card critical"><div class="stat-label">严重</div><div class="stat-value">{{ stats.critical || 0 }}</div></div>
      <div class="stat-card" style="border-left: 3px solid var(--rs-warning);"><div class="stat-label">高危</div><div class="stat-value">{{ stats.high || 0 }}</div></div>
      <div class="stat-card info"><div class="stat-label">中危</div><div class="stat-value">{{ stats.medium || 0 }}</div></div>
      <div class="stat-card success"><div class="stat-label">修复率</div><div class="stat-value">{{ stats.fix_rate || 0 }}%</div></div>
    </div>

    <!-- Filters -->
    <div style="display: flex; gap: 8px; margin-bottom: 12px;">
      <el-select v-model="filterSev" placeholder="等级" clearable size="small" style="width: 100px;" @change="currentPage = 1; load()">
        <el-option value="critical" label="严重" /><el-option value="high" label="高危" />
        <el-option value="medium" label="中危" /><el-option value="low" label="低危" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="修复状态" clearable size="small" style="width: 120px;" @change="currentPage = 1; load()">
        <el-option value="unfixed" label="未修复" /><el-option value="fixing" label="修复中" />
        <el-option value="fixed" label="已修复" />
      </el-select>
    </div>

    <el-table :data="findings" style="width: 100%;" @selection-change="onSelect" @row-click="openDetail">
      <el-table-column type="selection" width="40" />
      <el-table-column prop="title" label="漏洞名称" min-width="250" />
      <el-table-column prop="severity" label="等级" width="90">
        <template #default="{ row }"><span class="severity-badge" :class="row.severity">{{ row.severity }}</span></template>
      </el-table-column>
      <el-table-column prop="vuln_type" label="类型" width="120" />
      <el-table-column prop="cvss_score" label="CVSS" width="70">
        <template #default="{ row }">{{ row.cvss_score || '-' }}</template>
      </el-table-column>
      <el-table-column prop="combined_risk_score" label="综合风险" width="90">
        <template #default="{ row }">
          <span v-if="row.combined_risk_score" :style="{ color: row.combined_risk_score >= 8 ? 'var(--rs-danger)' : row.combined_risk_score >= 5 ? 'var(--rs-warning)' : 'var(--rs-success)' }">
            {{ row.combined_risk_score }}
          </span>
          <span v-else style="color: var(--rs-text-secondary);">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="found_by" label="来源" width="100" />
      <el-table-column prop="fix_status" label="修复状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.fix_status === 'fixed' ? 'success' : row.fix_status === 'fixing' ? 'warning' : 'danger'" size="small">
            {{ {unfixed:'未修复', fixing:'修复中', fixed:'已修复', reopen:'复发'}[row.fix_status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_verified" label="已验证" width="80">
        <template #default="{ row }">{{ row.is_verified ? '✅' : '⏳' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click.stop="openDetail(row)">详情</el-button>
          <el-button size="small" type="danger" @click.stop="deleteFinding(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Finding Detail Drawer -->
    <el-pagination v-if="totalFindings > pageSize" :current-page="currentPage" :page-size="pageSize" :total="totalFindings" @current-change="(p) => { currentPage = p; load() }" layout="prev, pager, next, total" style="margin-top: 12px; justify-content: flex-end;" />

    <el-drawer v-model="showDetail" :title="detailFinding?.title" size="600px">
      <div v-if="detailFinding" style="padding: 0 8px;">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <span class="severity-badge" :class="detailFinding.severity">{{ detailFinding.severity }}</span>
          <el-tag size="small">{{ detailFinding.vuln_type }}</el-tag>
          <el-tag v-if="detailFinding.cvss_score" size="small" type="warning">CVSS {{ detailFinding.cvss_score }}</el-tag>
        </div>

        <h4 style="margin: 16px 0 8px; color: var(--rs-text-primary);">漏洞描述</h4>
        <div style="font-size: 13px; white-space: pre-wrap; color: var(--rs-text-secondary);">{{ detailFinding.description || '无描述' }}</div>

        <h4 style="margin: 16px 0 8px; color: var(--rs-text-primary);">复现步骤</h4>
        <div style="font-size: 13px; white-space: pre-wrap; color: var(--rs-text-secondary);">{{ detailFinding.detail || '无复现步骤' }}</div>

        <h4 style="margin: 16px 0 8px; color: var(--rs-text-primary);">修复建议</h4>
        <div style="font-size: 13px; white-space: pre-wrap; color: var(--rs-text-secondary);">{{ detailFinding.solution || '无修复建议' }}</div>

        <div style="margin: 12px 0;">
          <el-button size="small" @click="aiGenerateDesc" :loading="aiGenerating">AI 生成描述/修复建议</el-button>
        </div>

        <h4 style="margin: 16px 0 8px; color: var(--rs-text-primary);">修复状态</h4>
        <div style="display: flex; gap: 8px;">
          <el-button size="small" :type="detailFinding.fix_status === 'fixed' ? 'success' : ''" @click="updateStatus(detailFinding.id, 'fixed')">已修复</el-button>
          <el-button size="small" :type="detailFinding.fix_status === 'fixing' ? 'warning' : ''" @click="updateStatus(detailFinding.id, 'fixing')">修复中</el-button>
          <el-button size="small" :type="detailFinding.fix_status === 'unfixed' ? 'danger' : ''" @click="updateStatus(detailFinding.id, 'unfixed')">未修复</el-button>
          <el-button size="small" type="info" @click="showRiskAccept = true">客户接受风险</el-button>
        </div>

        <!-- Risk Acceptance -->
        <div v-if="detailFinding.fix_status === 'accepted'" style="margin-top: 12px; padding: 10px; background: var(--rs-bg-secondary); border-radius: 6px; border-left: 3px solid var(--rs-warning);">
          <div style="font-size: 13px; color: var(--rs-warning);">客户已接受该风险</div>
        </div>

        <!-- Screenshots for this finding -->
        <div style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px; color: var(--rs-text-primary);">截图证据</h4>
          <el-upload
            :action="`/api/v1/projects/${pid}/screenshots?finding_id=${detailFinding.id}`"
            :headers="uploadHeaders"
            :on-success="onFindingScreenshot"
            :show-file-list="false"
            accept=".png,.jpg,.jpeg,.gif"
          >
            <el-button size="small">上传截图</el-button>
          </el-upload>
          <div v-if="findingScreenshots.length" style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;">
            <img v-for="s in findingScreenshots" :key="s.id" :src="s.view_url" style="width: 120px; border-radius: 4px; cursor: pointer;" @click="previewImage(s.view_url)" />
          </div>
        </div>

        <div v-if="detailFinding.evidence" style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px; color: var(--rs-text-primary);">证据</h4>
          <pre style="font-size: 12px; background: var(--rs-bg-secondary); padding: 12px; border-radius: 6px; overflow: auto; max-height: 300px;">{{ JSON.stringify(detailFinding.evidence, null, 2) }}</pre>
        </div>
      </div>
    </el-drawer>

    <!-- Risk Acceptance Dialog -->
    <el-dialog v-model="showRiskAccept" title="客户风险接受" width="480px">
      <el-form :model="riskForm" label-width="80px">
        <el-form-item label="客户名称"><el-input v-model="riskForm.client_name" /></el-form-item>
        <el-form-item label="接受人"><el-input v-model="riskForm.accepted_by" placeholder="客户方负责人" /></el-form-item>
        <el-form-item label="接受原因"><el-input v-model="riskForm.reason" type="textarea" :rows="3" placeholder="客户不修复的理由" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRiskAccept = false">取消</el-button>
        <el-button type="warning" @click="acceptRisk">确认接受风险</el-button>
      </template>
    </el-dialog>

    <!-- Add Finding Dialog -->
    <el-dialog v-model="showAdd" title="手动录入漏洞" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="漏洞名称" required><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="漏洞类型"><el-select v-model="form.vuln_type">
          <el-option v-for="t in ['sqli','xss','rce','file_upload','ssrf','xxe','auth_bypass','info_leak','csrf','lfi']" :key="t" :value="t" :label="t" />
        </el-select></el-form-item>
        <el-form-item label="严重程度"><el-select v-model="form.severity">
          <el-option value="critical" label="严重" /><el-option value="high" label="高危" />
          <el-option value="medium" label="中危" /><el-option value="low" label="低危" /><el-option value="info" label="信息" />
        </el-select></el-form-item>
        <el-form-item label="漏洞描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="复现步骤"><el-input v-model="form.detail" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="修复建议"><el-input v-model="form.solution" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="addFinding">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../stores/api'
import { logSessionActivity } from '../stores/api'

const route = useRoute()
const pid = route.params.id
const findings = ref([])
const totalFindings = ref(0)
const stats = ref({})
const showAdd = ref(false)
const showDetail = ref(false)
const detailFinding = ref(null)
const selectedIds = ref([])
const filterSev = ref('')
const filterStatus = ref('')
const form = ref({ title: '', vuln_type: 'sqli', severity: 'high', description: '', detail: '', solution: '' })
const showRiskAccept = ref(false)
const riskForm = ref({ client_name: '', accepted_by: '', reason: '' })
const findingScreenshots = ref([])
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }
const aiGenerating = ref(false)

const previewImage = (url) => { window.open(url, '_blank') }

const pageSize = ref(20)
const currentPage = ref(1)

const load = async () => {
  try {
    const params = { page: currentPage.value, page_size: pageSize.value }
    if (filterSev.value) params.severity = filterSev.value
    if (filterStatus.value) params.fix_status = filterStatus.value
    const [res, st] = await Promise.all([api.get(`/projects/${pid}/findings`, { params }), api.get(`/projects/${pid}/findings/stats`)])
    findings.value = res.items || []
    totalFindings.value = res.total || 0
    stats.value = { ...st.severities, fix_rate: st.fix_rate }
  } catch (e) { ElMessage.error('加载漏洞列表失败') }
}

const addFinding = async () => {
  await api.post(`/projects/${pid}/findings`, form.value)
  showAdd.value = false
  logSessionActivity(pid, '手动录入漏洞', form.value.title)
  await load()
}

const openDetail = (row) => {
  detailFinding.value = row
  showDetail.value = true
  loadFindingScreenshots(row.id)
}

const loadFindingScreenshots = async (findingId) => {
  try { const res = await api.get(`/projects/${pid}/screenshots`, { params: { finding_id: findingId } }); findingScreenshots.value = res.items || [] }
  catch { findingScreenshots.value = [] }
}

const onFindingScreenshot = () => {
  ElMessage.success('截图已上传')
  if (detailFinding.value) loadFindingScreenshots(detailFinding.value.id)
}

const aiGenerateDesc = async () => {
  if (!detailFinding.value) return
  aiGenerating.value = true
  try {
    const res = await api.post(`/projects/${pid}/ai-vuln-description`, {
      title: detailFinding.value.title,
      vuln_type: detailFinding.value.vuln_type,
      severity: detailFinding.value.severity,
      raw_detail: detailFinding.value.detail || '',
    })
    if (res.description) {
      await api.put(`/projects/${pid}/findings/${detailFinding.value.id}`, { description: res.description, solution: res.solution })
      detailFinding.value.description = res.description
      detailFinding.value.solution = res.solution
      ElMessage.success('AI 描述已生成并保存')
    } else {
      ElMessage.warning(res.error || 'AI 生成失败')
    }
  } catch (e) { ElMessage.error('AI 生成失败，请确认已配置 LLM API Key') }
  finally { aiGenerating.value = false }
}

const acceptRisk = async () => {
  if (!detailFinding.value) return
  try {
    await api.post(`/projects/${pid}/findings/${detailFinding.value.id}/accept-risk`, riskForm.value)
    ElMessage.success('风险已接受')
    showRiskAccept.value = false
    detailFinding.value.fix_status = 'accepted'
    riskForm.value = { client_name: '', accepted_by: '', reason: '' }
    await load()
  } catch (e) { ElMessage.error('操作失败') }
}

const onSelect = (rows) => { selectedIds.value = rows.map(r => r.id) }

const updateStatus = async (id, status) => {
  await api.put(`/projects/${pid}/findings/${id}`, { fix_status: status })
  detailFinding.value.fix_status = status
  await load()
}

const deleteFinding = async (row) => {
  await ElMessageBox.confirm(`确认删除漏洞「${row.title}」？此操作不可恢复。`, '删除确认', { type: 'warning' })
  await api.delete(`/projects/${pid}/findings/${row.id}`)
  ElMessage.success('已删除')
  await load()
}

const batchMarkFixed = async () => {
  await ElMessageBox.confirm(`确认将 ${selectedIds.value.length} 个漏洞标记为已修复？`, '批量操作', { type: 'info' })
  for (const id of selectedIds.value) {
    await api.put(`/projects/${pid}/findings/${id}`, { fix_status: 'fixed' })
  }
  ElMessage.success('已批量标记')
  await load()
}

const batchMarkFP = async () => {
  await ElMessageBox.confirm(`确认将 ${selectedIds.value.length} 个漏洞标记为误报？`, '批量操作', { type: 'warning' })
  for (const id of selectedIds.value) {
    await api.put(`/projects/${pid}/findings/${id}`, { is_false_positive: true })
  }
  ElMessage.success('已批量标记')
  await load()
}

onMounted(load)
</script>
