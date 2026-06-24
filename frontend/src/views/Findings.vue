<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>漏洞列表</h2>
      <el-button type="primary" size="small" @click="showAdd = true"><el-icon><Plus /></el-icon> 手动录入</el-button>
    </div>
    <div class="stat-grid" style="margin-bottom: 16px;">
      <div class="stat-card critical"><div class="stat-label">严重</div><div class="stat-value">{{ stats.critical || 0 }}</div></div>
      <div class="stat-card" style="border-left: 3px solid var(--rs-warning);"><div class="stat-label">高危</div><div class="stat-value">{{ stats.high || 0 }}</div></div>
      <div class="stat-card info"><div class="stat-label">中危</div><div class="stat-value">{{ stats.medium || 0 }}</div></div>
      <div class="stat-card success"><div class="stat-label">修复率</div><div class="stat-value">{{ stats.fix_rate || 0 }}%</div></div>
    </div>
    <el-table :data="findings" style="width: 100%;">
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
    </el-table>

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
import api from '../stores/api'

const route = useRoute()
const pid = route.params.id
const findings = ref([])
const stats = ref({})
const showAdd = ref(false)
const form = ref({ title: '', vuln_type: 'sqli', severity: 'high', description: '', detail: '', solution: '' })

const load = async () => {
  const [res, st] = await Promise.all([api.get(`/projects/${pid}/findings`), api.get(`/projects/${pid}/findings/stats`)])
  findings.value = res.items || []; stats.value = { ...st.severities, fix_rate: st.fix_rate }
}
const addFinding = async () => { await api.post(`/projects/${pid}/findings`, form.value); showAdd.value = false; await load() }
onMounted(load)
</script>
