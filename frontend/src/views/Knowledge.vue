<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>漏洞情报库</h2>
      <div style="display: flex; gap: 8px; align-items: center;">
        <el-button size="small" type="primary" @click="showAdd = true"><el-icon><Plus /></el-icon> 手动添加</el-button>
        <el-button size="small" @click="fetchNVD" :loading="fetchingNVD">抓取 NVD</el-button>
        <el-button size="small" @click="fetchCNVD" :loading="fetchingCNVD">抓取 CNVD</el-button>
      </div>
    </div>
    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
      <el-input v-model="keyword" placeholder="搜索漏洞..." style="width: 300px;" @keyup.enter="search" />
      <el-select v-model="severity" placeholder="等级" clearable style="width: 120px;" @change="search">
        <el-option value="critical" label="严重" /><el-option value="high" label="高危" /><el-option value="medium" label="中危" />
      </el-select>
      <el-button type="primary" @click="search">搜索</el-button>
    </div>
    <el-table :data="pagedItems" style="width: 100%;">
      <el-table-column prop="title" label="漏洞名称" min-width="300" />
      <el-table-column prop="cve_id" label="CVE" width="160" />
      <el-table-column prop="cnvd_id" label="CNVD" width="160" />
      <el-table-column prop="severity" label="等级" width="90"><template #default="{ row }"><span class="severity-badge" :class="row.severity">{{ row.severity }}</span></template></el-table-column>
      <el-table-column prop="affected_software" label="影响软件" width="150" />
      <el-table-column prop="weapon_stage" label="武器化" width="120">
        <template #default="{ row }">
          <el-tag :type="{disclosed:'info',poc_available:'warning',exp_available:'danger',in_the_wild:'danger'}[row.weapon_stage]" size="small">
            {{ {disclosed:'已披露',poc_available:'有PoC',exp_available:'有EXP',in_the_wild:'在野利用',mass_exploitation:'大规模利用'}[row.weapon_stage] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="has_poc" label="PoC" width="60"><template #default="{ row }">{{ row.has_poc ? '✅' : '❌' }}</template></el-table-column>
    </el-table>
    <el-pagination v-if="items.length > pageSize" :current-page="currentPage" :page-size="pageSize" :total="items.length" @current-change="currentPage = $event" layout="prev, pager, next, total" style="margin-top: 12px; justify-content: flex-end;" />

    <!-- Add Vuln Dialog -->
    <el-dialog v-model="showAdd" title="手动添加漏洞情报" width="560px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="漏洞名称" required><el-input v-model="addForm.title" /></el-form-item>
        <el-form-item label="CVE ID"><el-input v-model="addForm.cve_id" placeholder="CVE-2025-XXXX" /></el-form-item>
        <el-form-item label="CNVD ID"><el-input v-model="addForm.cnvd_id" placeholder="CNVD-2025-XXXX" /></el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="addForm.severity">
            <el-option value="critical" label="严重" /><el-option value="high" label="高危" />
            <el-option value="medium" label="中危" /><el-option value="low" label="低危" />
          </el-select>
        </el-form-item>
        <el-form-item label="影响软件"><el-input v-model="addForm.affected_software" /></el-form-item>
        <el-form-item label="影响厂商"><el-input v-model="addForm.affected_vendor" /></el-form-item>
        <el-form-item label="影响版本"><el-input v-model="addForm.affected_versions" placeholder="如: <= 10.58.2" /></el-form-item>
        <el-form-item label="漏洞类型">
          <el-select v-model="addForm.vuln_type">
            <el-option v-for="t in ['sqli','xss','rce','ssrf','lfi','xxe','auth_bypass','info_leak','deserialization','file_upload']" :key="t" :value="t" :label="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="武器化阶段">
          <el-select v-model="addForm.weapon_stage">
            <el-option value="disclosed" label="已披露" /><el-option value="poc_available" label="有PoC" />
            <el-option value="exp_available" label="有EXP" /><el-option value="in_the_wild" label="在野利用" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="addForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="修复建议"><el-input v-model="addForm.solution" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="addKnowledge">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const keyword = ref(''); const severity = ref(''); const items = ref([])
const fetchingNVD = ref(false); const fetchingCNVD = ref(false)
const pageSize = ref(20); const currentPage = ref(1)
const showAdd = ref(false)
const addForm = ref({ title: '', cve_id: '', cnvd_id: '', severity: 'high', affected_software: '', affected_vendor: '', affected_versions: '', vuln_type: 'rce', weapon_stage: 'disclosed', description: '', solution: '' })

const pagedItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

const search = async () => {
  try {
    const res = await api.get('/knowledge', { params: { keyword: keyword.value || undefined, severity: severity.value || undefined } })
    items.value = res.items || []
    currentPage.value = 1
  } catch (e) { ElMessage.error('搜索失败') }
}

const addKnowledge = async () => {
  if (!addForm.value.title) { ElMessage.warning('请输入漏洞名称'); return }
  try {
    await api.post('/knowledge', addForm.value)
    showAdd.value = false
    ElMessage.success('漏洞情报已添加')
    addForm.value = { title: '', cve_id: '', cnvd_id: '', severity: 'high', affected_software: '', affected_vendor: '', affected_versions: '', vuln_type: 'rce', weapon_stage: 'disclosed', description: '', solution: '' }
    await search()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '添加失败') }
}

const fetchNVD = async () => {
  fetchingNVD.value = true
  try {
    await api.post('/knowledge/fetch-nvd')
    ElMessage.success('NVD 抓取任务已提交')
    await search()
  } catch (e) { ElMessage.error(e.response?.data?.detail || 'NVD 抓取失败') }
  finally { fetchingNVD.value = false }
}

const fetchCNVD = async () => {
  fetchingCNVD.value = true
  try {
    await api.post('/knowledge/fetch-cnvd')
    ElMessage.success('CNVD 抓取任务已提交')
    await search()
  } catch (e) { ElMessage.error('CNVD 抓取失败') }
  finally { fetchingCNVD.value = false }
}

onMounted(search)
</script>
