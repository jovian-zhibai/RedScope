<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>漏洞情报库</h2>
      <div style="display: flex; gap: 8px;">
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const keyword = ref(''); const severity = ref(''); const items = ref([])
const fetchingNVD = ref(false); const fetchingCNVD = ref(false)
const pageSize = ref(20); const currentPage = ref(1)

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

const fetchNVD = async () => {
  fetchingNVD.value = true
  try {
    const res = await api.post('/knowledge/fetch-nvd')
    ElMessage.success(`NVD 抓取完成: 新增 ${res.added || 0} 条`)
    await search()
  } catch (e) { ElMessage.error('NVD 抓取失败') }
  finally { fetchingNVD.value = false }
}

const fetchCNVD = async () => {
  fetchingCNVD.value = true
  try {
    const res = await api.post('/knowledge/fetch-cnvd')
    ElMessage.success(`CNVD 抓取完成: 新增 ${res.added || 0} 条`)
    await search()
  } catch (e) { ElMessage.error('CNVD 抓取失败') }
  finally { fetchingCNVD.value = false }
}

onMounted(search)
</script>
